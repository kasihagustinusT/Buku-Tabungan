import logging
import json
import os
from datetime import date, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    CallbackContext,
    ContextTypes,
)

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Token dan Owner ID langsung didefinisikan di sini
TOKEN = "7947524305:AAEurXt7P280cv4kFFK4uWohE-eTPW-mZS4"
OWNER_ID = 6438135262

# File status
STATUS_FILE = "status.json"

# Konstanta target
TOTAL_TARGET_HARI = 1095
NABUNG_PER_HARI = 20000

def load_status() -> dict:
    try:
        with open(STATUS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_status(status: dict) -> None:
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)

def today_key() -> str:
    return date.today().strftime("%d-%b-%Y")

def build_main_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("✅ Sudah Nabung Hari Ini", callback_data="check_today")],
        [InlineKeyboardButton("📊 Lihat Progress", callback_data="progress")],
        [InlineKeyboardButton("📅 Statistik Bulan Ini", callback_data="statistik")],
        [InlineKeyboardButton("🎯 Target 3 Tahun", callback_data="target3tahun")],
        [InlineKeyboardButton("📂 Laporan JSON", callback_data="laporanjson")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_handler(update: Update, context: CallbackContext) -> None:
    if update.message:
        await update.message.reply_text(
            "Selamat datang di Buku Tabungan!\n\nGunakan tombol di bawah untuk mulai:",
            reply_markup=build_main_menu(),
        )
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "Selamat datang di Buku Tabungan!\n\nGunakan tombol di bawah untuk mulai:",
            reply_markup=build_main_menu(),
        )

async def button_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "check_today":
        await handle_check_today(query)
    elif data == "progress":
        await show_progress(query)
    elif data == "statistik":
        await show_statistik(query)
    elif data == "target3tahun":
        await show_target3tahun(query)
    elif data == "laporanjson":
        await send_laporan_json(query)
    elif data == "menu":
        await start_handler(query, context)

async def handle_check_today(query) -> None:
    status = load_status()
    key = today_key()
    status[key] = True
    save_status(status)

    await query.edit_message_text(
        f"✅ Tabungan untuk hari ini ({key}) berhasil dicentang!",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🏠 Kembali ke Menu", callback_data="menu")]]
        ),
    )

async def show_progress(query) -> None:
    status = load_status()
    done = sum(1 for v in status.values() if v)
    total = len(status)
    total_uang = done * NABUNG_PER_HARI

    await query.edit_message_text(
        f"📊 Progress Tabungan\n\n"
        f"✅ Sudah nabung: {done}/{total} hari\n"
        f"💰 Total terkumpul: Rp{total_uang:,}",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🏠 Kembali ke Menu", callback_data="menu")]]
        ),
    )

async def show_statistik(query) -> None:
    status = load_status()
    bulan_ini = date.today().strftime("%b-%Y")
    bulan_status = {k: v for k, v in status.items() if k.endswith(bulan_ini)}
    done = sum(1 for v in bulan_status.values() if v)
    total = len(bulan_status)
    total_uang = done * NABUNG_PER_HARI

    await query.edit_message_text(
        f"📅 Statistik Bulan Ini ({bulan_ini})\n\n"
        f"✅ Sudah nabung: {done}/{total} hari\n"
        f"💰 Total bulan ini: Rp{total_uang:,}",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🏠 Kembali ke Menu", callback_data="menu")]]
        ),
    )

async def show_target3tahun(query) -> None:
    status = load_status()
    done = sum(1 for v in status.values() if v)
    persen = done / TOTAL_TARGET_HARI * 100
    sisa = TOTAL_TARGET_HARI - done
    total_uang = done * NABUNG_PER_HARI

    await query.edit_message_text(
        f"🎯 Target 3 Tahun Nabung\n\n"
        f"✅ Hari sudah nabung: {done} hari\n"
        f"📈 Progress: {persen:.2f}%\n"
        f"📅 Hari tersisa: {sisa} hari\n"
        f"💰 Total terkumpul: Rp{total_uang:,}",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🏠 Kembali ke Menu", callback_data="menu")]]
        ),
    )

async def send_laporan_json(query) -> None:
    if os.path.exists(STATUS_FILE):
        await query.edit_message_text("Mengirim laporan JSON...")
        await query.message.reply_document(
            document=InputFile(STATUS_FILE),
            caption="📂 Berikut file laporan JSON tabungan kamu"
        )
    else:
        await query.edit_message_text(
            "❗ Belum ada data untuk dilaporkan.",
            reply_markup=build_main_menu()
        )

async def laporanjson_command(update: Update, context: CallbackContext) -> None:
    if os.path.exists(STATUS_FILE):
        await update.message.reply_document(InputFile(STATUS_FILE))
    else:
        await update.message.reply_text("❗ Belum ada data untuk dilaporkan.")

async def daily_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = context.job.data
    today = date.today().strftime("%d-%b-%Y")
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"⏰ Jangan lupa nabung hari ini ({today})!\nKlik /start untuk menandai hari ini."
    )

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("laporanjson", laporanjson_command))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Reminder harian jam 07:00 ke owner
    application.job_queue.run_daily(
        daily_reminder,
        time(hour=7, minute=0),
        days=(0, 1, 2, 3, 4, 5, 6),
        data=OWNER_ID,
        name=str(OWNER_ID),
    )

    application.run_polling()

if __name__ == "__main__":
    main()
