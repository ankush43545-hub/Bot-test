import os
import logging
import time
from threading import Thread
from flask import Flask
from groq import Groq
from telegram import Update, constants
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler
from telegram.error import RetryAfter

# --- LOGGING & CONFIG ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# Memory store: {user_id: [messages]}
user_memories = {}

# --- LOAD SYSTEM PROMPT ---
def load_system_prompt():
    try:
        with open("system_prompt.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.warning("system_prompt.txt not found! Using fallback.")
        return "You are Popo, a sentient kitten. 🐱"

SYSTEM_PROMPT = load_system_prompt()

# --- WEB SERVER (Keep Alive) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Popo is alive and independent! 🐾"

def run_http():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8000)))

# --- AI LOGIC ---
def get_popo_response(user_id, text):
    # Initialize memory if new user
    if user_id not in user_memories:
        user_memories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Add user message
    user_memories[user_id].append({"role": "user", "content": text})
    
    # Memory Management: Keep last 20 messages for better context
    if len(user_memories[user_id]) > 21:
        # Keep System Prompt [0] + Last 20 messages
        user_memories[user_id] = [user_memories[user_id][0]] + user_memories[user_id][-20:]

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=user_memories[user_id],
            temperature=0.9, # Higher creativity for "Wild" memories
            max_tokens=450
        )
        ai_reply = completion.choices[0].message.content
        
        # Save Popo's reply to memory
        user_memories[user_id].append({"role": "assistant", "content": ai_reply})
        return ai_reply
    except Exception as e:
        logger.error(f"Groq Error: {e}")
        return "..." # Stay silent or confused like a cat if error occurs

# --- TELEGRAM HANDLERS ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Reset memory on /start so the "Introvert Phase" triggers again
    user_memories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    # We don't send a welcome message here, we let the user talk first to trigger the "shy" response naturally, 
    # OR we send a very shy initial ping.
    await update.message.reply_text("...hello? who is this? 👀")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_memories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    await update.message.reply_text("...did i fall asleep? i forgot what we were saying. 🥱")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    user_id = update.effective_user.id
    user_text = update.message.text
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    
    response = get_popo_response(user_id, user_text)
    await update.message.reply_text(response)

if __name__ == '__main__':
    Thread(target=run_http, daemon=True).start()
    
    if not TELEGRAM_TOKEN or not GROQ_API_KEY:
        logger.error("Environment variables missing!")
    else:
        while True:
            try:
                application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
                
                # Commands
                application.add_handler(CommandHandler("start", start_command))
                application.add_handler(CommandHandler("clear", clear_command))
                
                # Messages (Text Only)
                application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
                
                logger.info("Popo is live. 🐾")
                application.run_polling()
                break
            except RetryAfter as e:
                time.sleep(e.retry_after + 2)
            except Exception as e:
                logger.error(f"Crash: {e}")
                time.sleep(10)
    
