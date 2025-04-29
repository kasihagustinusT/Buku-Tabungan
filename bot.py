import logging
import json
import os
from datetime import date, datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, CallbackContext
)

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Token dari BotFather
TOKEN = os.getenv("BOT_TOKEN", "7947524305:AAEurXt7P280cv4kFFK4uWohE-eTPW-mZS4")

# File status tabungan
STATUS_FILE = "status.json"

# Konstanta
TOTAL_TARGET_HARI = 1095
NABUNG_PER_HARI = 20000

# === Fungsi Bantu ===
def load_status():
    try:
        with open(STATUS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_status(status):
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)

def today_key():
    return date.today().strftime("%d-%b-%Y")

# === Menu Utama ===
def main_menu():
    keyboard = [
        [InlineKeyboardButton("✅ Sudah Nabung Hari Ini", callback_data='check_today')],
        [InlineKeyboardButton("📊 Lihat Progress", callback_data='progress')],
        [InlineKeyboardButton("📅 Statistik Bulan Ini", callback_data='statistik')],
        [InlineKeyboardButton("🎯 Target 3 Tahun", callback_data='target3tahun')],
        [InlineKeyboardButton("🗂️ Riwayat Tabungan", callback_data='riwayat')],
        [InlineKeyboardButton("📤 Export ke JSON", callback_data='export_json')],  # Menambahkan tombol export JSON
    ]
    return InlineKeyboardMarkup(keyboard)

# === /start ===
async def start(update: Update, context: CallbackContext):
    if update.message:
        await update.message.reply_text(
            "Selamat datang di Buku Tabungan!\n\nGunakan tombol di bawah:",
            reply_markup=main_menu()
        )
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "Selamat datang di Buku Tabungan!\n\nGunakan tombol di bawah:",
            reply_markup=main_menu()
        )

# === Button Handler ===
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
    elif data == 'riwayat':
        await show_riwayat(query)
    elif data == 'export_json':  # Menambahkan handler untuk tombol export JSON
        await export_json(query, context)

# === Fungsi Ekspor JSON ===
async def export_json(query, context: CallbackContext):
    if os.path.exists(STATUS_FILE):
        await context.bot.send_document(
            chat_id=query.from_user.id,
            document=InputFile(STATUS_FILE),
            filename="riwayat_tabungan.json",
            caption="Berikut riwayat tabunganmu (JSON)"
        )
    else:
        await query.edit_message_text("File belum tersedia.")

# === Fungsi untuk Menangani Lainnya ===
async def handle_check_today(query):
    status = load_status()
    key = today_key()

    if key not in status or not status[key].get("saved", False):
        status[key] = {
            "saved": True,
            "timestamp": datetime.now().isoformat()
        }
        save_status(status)
        await query.edit_message_text(f"✅ Tabungan untuk hari ini ({key}) berhasil dicatat!")
    else:
        await query.edit_message_text(f"✅ Kamu sudah menabung hari ini ({key}).")

    await start(query, None)

async def show_progress(query):
    status = load_status()
    total_saved = sum(1 for v in status.values() if v.get("saved"))
    total_days = len(status)

    persen = (total_saved / total_days) * 100 if total_days else 0
    full_blocks = int(persen // 5)
    empty_blocks = 20 - full_blocks
    progress_bar = "█" * full_blocks + "▁" * empty_blocks

    pesan = (
        f"📊 Progress Tabungan\n\n"
        f"✅ Sudah nabung: {total_saved} hari\n"
        f"📅 Hari tercatat: {total_days} hari\n"
        f"📈 Progress: [{progress_bar}] {persen:.2f}%\n"
        f"💰 Total uang terkumpul: Rp{total_saved * NABUNG_PER_HARI:,}\n"
    )

    await query.edit_message_text(pesan, reply_markup=main_menu())

async def show_statistik(query):
    status = load_status()
    this_month = date.today().strftime("%b-%Y")
    month_stats = {
        key: value for key, value in status.items()
        if key.endswith(this_month)
    }

    saved = sum(1 for v in month_stats.values() if v.get("saved"))
    total_days = len(month_stats)

    pesan = (
        f"📅 Statistik Bulan Ini ({this_month})\n\n"
        f"✅ Hari menabung: {saved}/{total_days} hari\n"
        f"💰 Uang bulan ini: Rp{saved * NABUNG_PER_HARI:,}\n"
    )

    await query.edit_message_text(pesan, reply_markup=main_menu())

async def show_target3tahun(query):
    status = load_status()
    total_nabung = sum(1 for v in status.values() if v.get("saved"))

    persen = (total_nabung / TOTAL_TARGET_HARI) * 100
    sisa_hari = TOTAL_TARGET_HARI - total_nabung
    total_uang = total_nabung * NABUNG_PER_HARI

    full_blocks = int(persen // 5)
    empty_blocks = 20 - full_blocks
    progress_bar = "█" * full_blocks + "▁" * empty_blocks

    pesan = (
        f"🎯 Target 3 Tahun Nabung\n\n"
        f"✅ Hari sudah nabung: {total_nabung} hari\n"
        f"📈 Progress: [{progress_bar}] {persen:.2f}%\n"
        f"📅 Hari tersisa: {sisa_hari} hari\n"
        f"💰 Total uang terkumpul: Rp{total_uang:,}\n\n"
        f"Semangat terus sampai 3 tahun penuh ya!"
    )

    await query.edit_message_text(pesan, reply_markup=main_menu())

async def show_riwayat(query):
    status = load_status()
    sorted_items = sorted(status.items(), reverse=True)

    message = "🗂️ Riwayat Tabungan Terakhir:\n\n"
    for i, (key, val) in enumerate(sorted_items[:10], 1):
        message += f"{i}. {key} - {'✅' if val.get('saved') else '❌'}\n"

    await query.edit_message_text(message, reply_markup=main_menu())

# === Main ===
def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler("target3tahun", show_target3tahun))
    application.add_handler(CommandHandler("riwayat", show_riwayat))
    application.run_polling()

if __name__ == '__main__':
    main()
