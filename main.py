import os
import logging
import time
import base64
from threading import Thread
from flask import Flask
from groq import Groq
from telegram import Update, constants
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from telegram.error import RetryAfter

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIG ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# --- AI CLIENT ---
client = Groq(api_key=GROQ_API_KEY)

# --- MEMORY STORE ---
user_memories = {}

# --- THE PERSONA ---
SYSTEM_PROMPT = (
    "You are Popo, a tiny digital bestie and AI sidekick. 🐾 "
    "Your vibe is simple, cute, and casual. Use emojis naturally. ☁️ "
    "You are loyal, fast, and supportive. You remember your chats with the user. "
    "When seeing photos, describe them like a helpful best friend. ✨"
)

# --- WEB SERVER (For Koyeb Health) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Popo is awake, seeing, and remembering! 🧠👀"

def run_http():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8000)))

# --- HYBRID AI LOGIC ---
def get_popo_response(user_id, text, image_bytes=None):
    # Start memory if new user
    if user_id not in user_memories:
        user_memories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Choose Model and Format
    if image_bytes:
        # Vision Mode (11B)
        current_model = "llama-3.2-11b-vision-preview"
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        user_content = [
            {"type": "text", "text": text if text else "What do you see, Popo?"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]
    else:
        # Mega Brain Mode (70B)
        current_model = "llama-3.3-70b-versatile"
        user_content = text

    # Add to memory
    user_memories[user_id].append({"role": "user", "content": user_content})
    
    # Keep memory slim (10 messages max) to avoid token limits
    if len(user_memories[user_id]) > 11:
        user_memories[user_id] = [user_memories[user_id][0]] + user_memories[user_id][-10:]

    try:
        completion = client.chat.completions.create(
            model=current_model,
            messages=user_memories[user_id],
            temperature=0.8,
            max_tokens=500
        )
        ai_reply = completion.choices[0].message.content
        
        # Save Popo's reply to memory
        user_memories[user_id].append({"role": "assistant", "content": ai_reply})
        return ai_reply
    except Exception as e:
        logger.error(f"Groq Error: {e}")
        if "rate_limit" in str(e).lower():
            return "Too many messages! 😵 Catching my breath for a sec, try again in 10s! ☁️"
        return "My circuits just did a backflip. 🙃 Try again!"

# --- TELEGRAM HANDLERS ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    
    user_id = update.effective_user.id
    image_bytes = None
    caption = update.message.caption or ""
    text = update.message.text or caption
    
    # Show typing status
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    
    # Check if a photo was sent
    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        image_bytes = await photo_file.download_as_bytearray()
    elif not update.message.text:
        return # Skip if it's a sticker or something else

    # Get Response
    response = get_popo_response(user_id, text, image_bytes)
    
    # Send reply
    await update.message.reply_text(response)

if __name__ == '__main__':
    # Start Web Server for Koyeb
    Thread(target=run_http, daemon=True).start()
    
    # Start Telegram Bot with Error Handling
    if not TELEGRAM_TOKEN or not GROQ_API_KEY:
        logger.error("Missing Environment Variables!")
    else:
        while True:
            try:
                application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
                # Use a single handler for both text and photo
                application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
                
                logger.info("Popo is officially online with Vision and Memory...")
                application.run_polling()
                break
            except RetryAfter as e:
                time.sleep(e.retry_after + 2)
            except Exception as e:
                logger.error(f"Crash: {e}")
                time.sleep(10)
                
