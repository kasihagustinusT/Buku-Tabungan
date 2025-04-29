import logging
import json
import os
from datetime import date, datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, CallbackContext
)

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Token dari BotFather
TOKEN = os.getenv("BOT_TOKEN", "YOUR_TOKEN_HERE")

# Path ke file status tabungan
STATUS_FILE = "status.json"

# Konstanta Target
TOTAL_TARGET_HARI = 1095  # 3 tahun = 1095 hari
NABUNG_PER_HARI = 20000   # Rp 20.000 per hari

# === Fungsi Bantu ===
def load_status():
    if not os.path.exists(STATUS_FILE):
        save_status({})
    with open(STATUS_FILE, "r") as f:
        return json.load(f)

def save_status(status):
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)

def today_key():
    today = date.today()
    return today.strftime("%d-%b-%Y")

def ensure_today_exists():
    """Pastikan hari ini sudah ada di status.json"""
    status = load_status()
    key = today_key()
    if key not in status:
        status[key] = False
        save_status(status)

# === Tampilan Menu Utama ===
def main_menu():
    keyboard = [
        [InlineKeyboardButton("✅ Sudah Nabung Hari Ini", callback_data='check_today')],
        [InlineKeyboardButton("📊 Lihat Progress", callback_data='progress')],
        [InlineKeyboardButton("📅 Statistik Bulan Ini", callback_data='statistik')],
        [InlineKeyboardButton("🎯 Target 3 Tahun", callback_data='target3tahun')],
    ]
    return InlineKeyboardMarkup(keyboard)

# === Command /start ===
async def start(update: Update, context: CallbackContext):
    ensure_today_exists()
    if update.message:
        await update.message.reply_text(
            "Selamat datang di Buku Tabungan!\n\nGunakan tombol di bawah untuk mulai:",
            reply_markup=main_menu()
        )
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "Selamat datang di Buku Tabungan!\n\nGunakan tombol di bawah untuk mulai:",
            reply_markup=main_menu()
        )

# === Handler Button ===
async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'check_today':
        await handle_check_today(query)
    elif data == 'progress':
        await show_progress(query)
    elif data == 'statistik':
        await show_statistik(query)
    elif data == 'target3tahun':
        await show_target3tahun(query)

# === Fungsi Tindakan ===
async def handle_check_today(query):
    status = load_status()
    key = today_key()

    status[key] = True
    save_status(status)

    await query.edit_message_text(f"✅ Tabungan untuk hari ini ({key}) berhasil dicentang!\n\nKembali ke menu awal.")
    await start(query, None)

async def show_progress(query):
    ensure_today_exists()
    status = load_status()
    total_saved = sum(1 for v in status.values() if v)
    total_days = len(status)

    pesan = (
        f"📊 Progress Tabungan\n\n"
        f"✅ Sudah nabung: {total_saved} hari\n"
        f"📅 Total hari tercatat: {total_days} hari\n"
        f"💰 Total uang terkumpul: Rp{total_saved * NABUNG_PER_HARI:,}\n\n"
        f"Kembali ke menu awal."
    )

    await query.edit_message_text(pesan)
    await start(query, None)

async def show_statistik(query):
    ensure_today_exists()
    status = load_status()
    this_month = date.today().strftime("%b-%Y")
    month_stats = {key: value for key, value in status.items() if key.endswith(this_month)}

    saved = sum(1 for v in month_stats.values() if v)
    total_days = len(month_stats)

    pesan = (
        f"📅 Statistik Bulan Ini ({this_month})\n\n"
        f"✅ Hari menabung: {saved}/{total_days} hari\n"
        f"💰 Uang bulan ini: Rp{saved * NABUNG_PER_HARI:,}\n\n"
        f"Kembali ke menu awal."
    )

    await query.edit_message_text(pesan)
    await start(query, None)

async def show_target3tahun(query):
    ensure_today_exists()
    status = load_status()
    total_nabung = sum(1 for v in status.values() if v)

    persen = (total_nabung / TOTAL_TARGET_HARI) * 100
    sisa_hari = TOTAL_TARGET_HARI - total_nabung
    total_uang = total_nabung * NABUNG_PER_HARI

    pesan = (
        f"🎯 Target 3 Tahun Nabung\n\n"
        f"✅ Hari sudah nabung: {total_nabung} hari\n"
        f"📈 Progress: {persen:.2f}%\n"
        f"📅 Hari tersisa: {sisa_hari} hari\n"
        f"💰 Total uang terkumpul: Rp{total_uang:,}\n\n"
        f"Semangat terus sampai 3 tahun penuh ya!"
    )

    await query.edit_message_text(pesan)
    await start(query, None)

# === Fungsi Main ===
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler("target3tahun", show_target3tahun))  # Bisa dipanggil manual juga

    application.run_polling()

if __name__ == '__main__':
    main()
