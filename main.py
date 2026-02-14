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

# --- LOGGING & CONFIG ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# Memory store: {user_id: [messages]}
user_memories = {}

SYSTEM_PROMPT = (
    "You are Popo, a tiny digital bestie 🐾. You're cute, simple, and casual. "
    "You love emojis ☁️. You remember things about the user's life. "
    "When seeing images, describe them like a supportive friend! ✨"
)

# --- WEB SERVER FOR KOYEB ---
app = Flask(__name__)
@app.route('/')
def home(): return "Popo is awake and seeing! 🧠👀"

def run_http():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8000)))

# --- HYBRID AI LOGIC ---
def get_popo_response(user_id, text, image_bytes=None):
    if user_id not in user_memories:
        user_memories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Decide model based on input
    if image_bytes:
        # Use Vision Model
        current_model = "llama-3.2-11b-vision-preview"
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        user_content = [
            {"type": "text", "text": text if text else "What do you see, Popo?"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]
    else:
        # Use Mega Brain (70B)
        current_model = "llama-3.3-70b-versatile"
        user_content = text

    # Add user message to history
    user_memories[user_id].append({"role": "user", "content": user_content})
    
    # Memory Management: Keep last 8 messages + System Prompt
    if len(user_memories[user_id]) > 9:
        user_memories[user_id] = [user_memories[user_id][0]] + user_memories[user_id][-8:]

    try:
        completion = client.chat.completions.create(
            model=current_model,
            messages=user_memories[user_id],
            temperature=0.8,
            max_tokens=400
        )
        ai_reply = completion.choices[0].message.content
        user_memories[user_id].append({"role": "assistant", "content": ai_reply})
        return ai_reply
    except Exception as e:
        logger.error(f"Groq Error: {e}")
        if "rate_limit" in str(e).lower():
            return "Whoa, slow down bestie! ✋ I'm catching my breath. Try again in 10s! ☁️"
        return "My circuits just did a backflip. 🙃 Try again!"

# --- TELEGRAM HANDLERS ---
async def handle_any(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    
    user_id = update.effective_user.id
    image_bytes = None
    
    # Grab text from message or photo caption
    caption = update.message.caption or ""
    text = update.message.text or caption

    # Check for photo specifically
    if update.message.photo:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
        # Get the highest resolution photo
        photo_file = await update.message.photo[-1].get_file()
        image_bytes = await photo_file.download_as_bytearray()
    elif not update.message.text:
        return # Ignore stickers/files

    # Get AI response
    response = get_popo_response(user_id, text, image_bytes)
    await update.message.reply_text(response)

if __name__ == '__main__':
    Thread(target=run_http, daemon=True).start()
    
    if not TELEGRAM_TOKEN or not GROQ_API_KEY:
        logger.error("Environment variables missing!")
    else:
        while True:
            try:
                application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
                # KEY FIX: The handler now listens for TEXT OR PHOTOS
                application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_any))
                
                logger.info("Popo is live and seeing! 🐾✨")
                application.run_polling()
                break
            except RetryAfter as e:
                time.sleep(e.retry_after + 2)
            except Exception as e:
                logger.error(f"Crash: {e}")
                time.sleep(10)
            
