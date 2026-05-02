import os
import json
import requests
import gspread
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CommandHandler

# Şifreler – Render ortam değişkenlerinden otomatik alınır
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_KEY = os.getenv("GROQ_KEY")
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SHEET_ID = "1A1-r7vx7aTLbLpDpc0n-qvpiEhfybu3ZGmkkORHoCHw"

def get_sheet():
    """Google Sheets bağlantısını hazırlar."""
    creds = json.loads(GOOGLE_SHEETS_CREDENTIALS)
    gc = gspread.service_account_from_dict(creds)
    sh = gc.open_by_key(SHEET_ID)
    return sh.sheet1

def init_sheet():
    """Eğer tablo boşsa başlıkları koyar."""
    sheet = get_sheet()
    if not sheet.row_values(1):
        basliklar = ["Tarih", "Plaka", "Müşteri", "Şasi/Model",
                     "Arıza Kodu", "Yapılan İş", "Kullanılan Parça", "Notlar"]
        sheet.insert_row(basliklar, 1)
    return sheet

# /kaydet komutu
async def kaydet(update: Update, context):
    text = update.message.text.split(maxsplit=1)[1] if len(update.message.text.split()) > 1 else ""
    if not text:
        await update.message.reply_text("Örnek: /kaydet 34ABC123, Debriyaj balatası değişimi")
        return
    parcalar = [p.strip() for p in text.split(",")]
    if len(parcalar) < 2:
        await update.message.reply_text("Lütfen plaka ve işi virgülle ayırın.")
        return
    plaka, is_ = parcalar[0], parcalar[1]
    tarih = datetime.now().strftime("%d.%m.%Y %H:%M")
    sheet = get_sheet()
    sheet.append_row([tarih, plaka, "", "", "", is_, "", ""])
    await update.message.reply_text(f"✅ {plaka} → {is_} kaydedildi.")

# /rapor komutu
async def rapor(update: Update, context):
    sheet = get_sheet()
    kayitlar = sheet.get_all_records()
    if not kayitlar:
        await update.message.reply_text("Henüz hiç kayıt yok.")
        return
    mesaj = "📋 **Son 5 İşlem:**\n"
    for i, row in enumerate(kayitlar[-5:]):
        mesaj += f"{i+1}. {row.get('Tarih','?')} | {row.get('Plaka','?')} | {row.get('Yapılan İş','?')}\n"
    await update.message.reply_text(mesaj, parse_mode='Markdown')

# Normal sohbet (arıza teşhisi, parça arama vb.)
async def chat(update: Update, context):
    user_text = update.message.text
    sistem_prompt = """Sen 25 yıllık ağır vasıta/iş makinası tamircisisin. 
Motor, hidrolik, şanzıman, pnömatik, elektrik sistemlerinde uzmansın.
Arıza belirtilerini yazdığında önce olası nedenleri, sonra kontrol adımlarını sırala.
Parça kodu verildiğinde genel eşdeğerleri ve dikkat edilmesi gerekenleri söyle.
Cevabın daima pratik, atölyede kullanılabilir şekilde olsun."""
    
    headers = {"Authorization": f"Bearer {GROQ_KEY}"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": sistem_prompt},
            {"role": "user", "content": user_text}
        ]
    }
    resp = requests.post("https://api.groq.com/openai/v1/chat/completions",
                         headers=headers, json=payload).json()
    if "choices" in resp:
        reply = resp["choices"][0]["message"]["content"]
    else:
        reply = "⚠️ Hata oluştu, tekrar dener misin?"
    await update.message.reply_text(reply)

# Botu çalıştır
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    app.add_handler(CommandHandler("kaydet", kaydet))
    app.add_handler(CommandHandler("rapor", rapor))
    init_sheet()
    print("🤖 Mechanicer çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
