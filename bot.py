import logging
import json
import os
import csv
from datetime import date, datetime, timedelta
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
    CallbackQuery
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
STATUS_FILE = "status.json"
TARGET_FILE = "target.json"

# Helper Functions
def load_status() -> dict:
    try:
        with open(STATUS_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_status(status: dict) -> None:
    with open(STATUS_FILE, "w", encoding='utf-8') as f:
        json.dump(status, f, indent=2, ensure_ascii=False)

def today_key() -> str:
    return date.today().strftime("%d-%b-%Y")

def hitung_beruntun(status: dict) -> int:
    try:
        days = sorted(
            [datetime.strptime(k, "%d-%b-%Y").date() for k, v in status.items() if v.get("saved")],
            reverse=True
        )
        if not days:
            return 0
            
        streak = 1
        for i in range(1, len(days)):
            if days[i-1] - days[i] == timedelta(days=1):
                streak += 1
            else:
                break
        return streak
    except Exception as e:
        logger.error(f"Error calculating streak: {e}")
        return 0

def load_target() -> dict:
    try:
        with open(TARGET_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_target(data: dict) -> None:
    with open(TARGET_FILE, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def buat_progress_bar(persen: float, panjang: int = 10) -> str:
    persen = max(0, min(persen, 1.0))
    blok_terisi = int(round(persen * panjang))
    return "▓" * blok_terisi + "░" * (panjang - blok_terisi)

def format_rupiah(nominal: int) -> str:
    return f"Rp{nominal:,}".replace(",", ".")

def get_user_target(user_id: str) -> tuple:
    targets = load_target()
    return targets.get(str(user_id)), targets

# Menu Functions
def main_menu(user_id: str = None) -> InlineKeyboardMarkup:
    target, _ = get_user_target(user_id)
    
    keyboard = []
    
    if target:
        keyboard.extend([
            [InlineKeyboardButton("✅ Sudah Nabung Hari Ini", callback_data='check_today')],
            [InlineKeyboardButton("➕ Tambah Hari Sebelumnya", callback_data='tambah_sebelum')]
        ])
    
    keyboard.extend([
        [InlineKeyboardButton("📊 Lihat Progress", callback_data='progress')],
        [InlineKeyboardButton("📅 Statistik Bulan Ini", callback_data='statistik')],
        [InlineKeyboardButton("🎯 Target Nabung", callback_data='target_menu')],
        [InlineKeyboardButton("🗂️ Riwayat Tabungan", callback_data='riwayat')],
        [InlineKeyboardButton("📥 Download Riwayat", callback_data='download_riwayat')]
    ])
    
    return InlineKeyboardMarkup(keyboard)

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    target, _ = get_user_target(user_id)
    
    if not target:
        await show_target_menu(update, context)
        return
    
    text = (
        "💰 *Buku Tabungan Digital* 💰\n\n"
        f"Target harian Anda: {format_rupiah(target['per_hari'])}\n"
        "Gunakan menu di bawah untuk mulai:"
    )
    
    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu(user_id), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=main_menu(user_id), parse_mode="Markdown")

# Button Handlers
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    handlers = {
        'check_today': handle_check_today,
        'tambah_sebelum': tambah_sebelum,
        'progress': show_progress,
        'statistik': show_statistik,
        'target_menu': show_target_menu,
        'atur_target': atur_target_handler,
        'lihat_target': show_target_custom,
        'reset_target': reset_target_handler,
        'back_to_menu': start,
        'riwayat': show_riwayat,
        'download_riwayat': download_riwayat
    }

    handler = handlers.get(data)
    if handler:
        await handler(query, context)
    else:
        await query.edit_message_text("Perintah tidak dikenali. Silakan coba lagi.", reply_markup=main_menu(user_id))

# Savings Functions
async def handle_check_today(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = query.from_user.id
    target, _ = get_user_target(user_id)
    
    if not target:
        await query.edit_message_text("Anda belum mengatur target tabungan.", reply_markup=main_menu(user_id))
        return
    
    per_hari = target['per_hari']
    status = load_status()
    today = today_key()
    
    if today in status and status[today].get("saved"):
        await query.edit_message_text("⚠️ Kamu sudah menabung hari ini.", reply_markup=main_menu(user_id))
        return
    
    status[today] = {"saved": True, "amount": per_hari}
    save_status(status)
    
    streak = hitung_beruntun(status)
    total_hari = sum(1 for v in status.values() if v.get("saved"))
    total_uang = sum(v.get("amount", 0) for v in status.values() if v.get("saved"))
    
    response = (
        f"✅ *Nabung hari ini berhasil dicatat!*\n\n"
        f"💵 Jumlah: {format_rupiah(per_hari)}\n"
        f"🔥 *Streak:* {streak} hari berturut-turut\n"
        f"📊 *Total:* {total_hari} hari ({format_rupiah(total_uang)})\n\n"
        f"Teruskan kebiasaan baik ini!"
    )
    
    await query.edit_message_text(response, reply_markup=main_menu(user_id), parse_mode="Markdown")

async def tambah_sebelum(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = query.from_user.id
    target, _ = get_user_target(user_id)
    
    if not target:
        await query.edit_message_text("Anda belum mengatur target tabungan.", reply_markup=main_menu(user_id))
        return
    
    per_hari = target['per_hari']
    status = load_status()
    kemarin = (date.today() - timedelta(days=1)).strftime("%d-%b-%Y")
    
    if kemarin in status and status[kemarin].get("saved"):
        await query.edit_message_text("⚠️ Kamu sudah menabung kemarin.", reply_markup=main_menu(user_id))
        return
    
    status[kemarin] = {"saved": True, "amount": per_hari}
    save_status(status)
    
    await query.edit_message_text(
        "✅ *Nabung kemarin berhasil ditambahkan!*",
        reply_markup=main_menu(user_id),
        parse_mode="Markdown"
    )

async def show_progress(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = query.from_user.id
    status = load_status()
    total_hari = sum(1 for v in status.values() if v.get("saved"))
    total_uang = sum(v.get("amount", 0) for v in status.values() if v.get("saved"))
    streak = hitung_beruntun(status)
    
    target, _ = get_user_target(user_id)
    if target:
        target_text = f"\n🎯 Target Harian: {format_rupiah(target['per_hari'])}"
    else:
        target_text = ""
    
    response = (
        f"📊 *Progress Tabungan*{target_text}\n\n"
        f"✅ *Hari menabung:* {total_hari}\n"
        f"💰 *Total tabungan:* {format_rupiah(total_uang)}\n"
        f"🔥 *Streak saat ini:* {streak} hari\n\n"
        f"Terus semangat menabung!"
    )
    
    await query.edit_message_text(response, reply_markup=main_menu(user_id), parse_mode="Markdown")

async def show_target_menu(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = query.from_user.id
    target, _ = get_user_target(user_id)
    
    if target:
        text = f"🎯 Target tabungan Anda saat ini:\n*{format_rupiah(target['per_hari'])} per hari*"
    else:
        text = "Anda belum mengatur target tabungan.\n"
    
    await query.edit_message_text(text, reply_markup=main_menu(user_id), parse_mode="Markdown")

# Run the bot
def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    application.run_polling()

if __name__ == "__main__":
    main()
