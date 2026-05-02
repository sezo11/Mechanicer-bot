import os
import json
import requests
import gspread
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CommandHandler

# ---------- Ortam Değişkenleri ----------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_KEY = os.getenv("GROQ_KEY")
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SHEET_ID = "1A1-r7vx7aTLbLpDpc0n-qvpiEhfybu3ZGmkkORHoCHw"

# ---------- Google Sheets Bağlantısı ----------
def get_sheet():
    creds = json.loads(GOOGLE_SHEETS_CREDENTIALS)
    gc = gspread.service_account_from_dict(creds)
    sh = gc.open_by_key(SHEET_ID)
    return sh.sheet1

def init_sheet():
    sheet = get_sheet()
    if not sheet.row_values(1):
        basliklar = ["Tarih", "Plaka", "Müşteri", "Şasi/Model",
                     "Arıza Kodu", "Yapılan İş", "Kullanılan Parça", "Notlar"]
        sheet.insert_row(basliklar, 1)
    return sheet

# ---------- /kaydet Komutu ----------
async def kaydet(update: Update, context):
    try:
        args = update.message.text.split(maxsplit=1)[1]
    except IndexError:
        await update.message.reply_text("📝 Kullanım: /kaydet Plaka, Yapılan İş, Kullanılan Parça (opsiyonel)")
        return

    parcalar = [p.strip() for p in args.split(",")]
    if len(parcalar) < 2:
        await update.message.reply_text("⚠️ En az Plaka ve Yapılan İş gerekli.")
        return

    tarih = datetime.now().strftime("%d.%m.%Y %H:%M")
    plaka = parcalar[0]
    is_ = parcalar[1]
    parca = parcalar[2] if len(parcalar) > 2 else ""
    notlar = parcalar[3] if len(parcalar) > 3 else ""

    sheet = get_sheet()
    sheet.append_row([tarih, plaka, "", "", "", is_, parca, notlar])
    await update.message.reply_text(f"✅ {plaka} → {is_} kaydedildi.")

# ---------- /rapor Komutu ----------
async def rapor(update: Update, context):
    sheet = get_sheet()
    kayitlar = sheet.get_all_records()
    if not kayitlar:
        await update.message.reply_text("📭 Henüz hiç kayıt yok.")
        return

    # Eğer özel bir plaka filtresi verildiyse
    filtre = update.message.text.split()
    plaka_filtre = filtre[1].upper() if len(filtre) > 1 else None

    if plaka_filtre:
        kayitlar = [k for k in kayitlar if k.get("Plaka", "").upper() == plaka_filtre]
        if not kayitlar:
            await update.message.reply_text(f"🔍 {plaka_filtre} plakasına ait kayıt bulunamadı.")
            return

    # Son 10 kayıt
    mesaj = f"📋 **{'Tüm Araçlar' if not plaka_filtre else plaka_filtre}** (Son 10 İşlem):\n"
    for i, row in enumerate(kayitlar[-10:]):
        mesaj += f"{i+1}. {row.get('Tarih','?')} | {row.get('Plaka','?')} | {row.get('Yapılan İş','?')}\n"

    await update.message.reply_text(mesaj, parse_mode='Markdown')

# ---------- Ana Sohbet (Arıza Teşhis, Parça) ----------
async def chat(update: Update, context):
    user_text = update.message.text
    sistem_prompt = (
        "Sen 25 yıllık ağır vasıta ve iş makinası ustabaşı Mechanicer'sin. "
        "Motor, hidrolik, şanzıman, pnömatik fren, elektrik sistemlerinde uzmansın. "
        "Arıza kodları (DTC), belirtiler yazıldığında önce olası nedenleri, "
        "sonra hızlı kontrol adımlarını sırala. Parça kodu verildiğinde "
        "OEM eşdeğer numaralarını ve dikkat edilmesi gerekenleri söyle. "
        "Cevabın pratik, mümkünse maddeler halinde, sahada anında kullanılabilecek şekilde olsun. "
        "Türkçe konuş, bazen argo da kullanabilirsin ama saygılı kal."
    )

    headers = {"Authorization": f"Bearer {GROQ_KEY}"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": sistem_prompt},
            {"role": "user", "content": user_text}
        ]
    }

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        ).json()
        if "choices" in resp:
            reply = resp["choices"][0]["message"]["content"]
        else:
            reply = "⚠️ Groq API'de bir sorun var. Biraz sonra tekrar dene."
    except Exception as e:
        reply = f"⚠️ Bağlantı hatası: {e}"

    await update.message.reply_text(reply)

# ---------- Bot Başlatma ----------
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
