import os
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_KEY = os.getenv("GROQ_KEY")

async def chat(update: Update, context):
    user_text = update.message.text
    headers = {"Authorization": f"Bearer {GROQ_KEY}"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "Sen yardımsever, esprili bir asistansın. Adın Mechanicer."},
            {"role": "user", "content": user_text}
        ]
    }
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload
    ).json()
    
    if "choices" in resp:
        reply = resp["choices"][0]["message"]["content"]
    else:
        reply = "⚠️ Bir hata oluştu, lütfen tekrar dene."
    
    await update.message.reply_text(reply)

app = Application.builder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
print("🤖 Mechanicer çalışıyor...")
app.run_polling()
