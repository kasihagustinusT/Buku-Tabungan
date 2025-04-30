import logging
import json
import os
from datetime import date, datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, filters
)

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
STATUS_FILE = "status.json"
TARGET_FILE = "target.json"
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

def hitung_beruntun(status):
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

def load_target():
    try:
        with open(TARGET_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_target(data):
    with open(TARGET_FILE, "w") as f:
        json.dump(data, f, indent=2)

# === Menu Utama ===
def main_menu():
    keyboard = [
        [InlineKeyboardButton("✅ Sudah Nabung Hari Ini", callback_data='check_today')],
        [InlineKeyboardButton("➕ Tambah Hari Sebelumnya", callback_data='tambah_sebelum')],
        [InlineKeyboardButton("📊 Lihat Progress", callback_data='progress')],
        [InlineKeyboardButton("📅 Statistik Bulan Ini", callback_data='statistik')],
        [InlineKeyboardButton("🎯 Target Nabung", callback_data='target_menu')],
        [InlineKeyboardButton("🗂️ Riwayat Tabungan", callback_data='riwayat')],
        [InlineKeyboardButton("📥 Download Riwayat", callback_data='download_riwayat')]
    ]
    return InlineKeyboardMarkup(keyboard)

# === Command ===
async def start(update: Update, context: CallbackContext):
    if update.message:
        await update.message.reply_text("Selamat datang di Buku Tabungan!\n\nGunakan tombol di bawah:", reply_markup=main_menu())
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Selamat datang di Buku Tabungan!\n\nGunakan tombol di bawah:", reply_markup=main_menu())

# === Handler Button ===
async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'check_today':
        await handle_check_today(query)
    elif data == 'tambah_sebelum':
        await tambah_sebelum(query)
    elif data == 'progress':
        await show_progress(query)
    elif data == 'statistik':
        await show_statistik(query)
    elif data == 'target_menu':
        await show_target_menu(query)
    elif data == 'atur_target':
        await query.edit_message_text("Silakan kirim durasi menabung dan tanggal mulai dalam format:\n\n`365 2025-05-01`\n\nArtinya: menabung selama 365 hari mulai 1 Mei 2025.", parse_mode="Markdown")
        context.user_data["awaiting_target_input"] = True
    elif data == 'lihat_target':
        await show_target_custom(query)
    elif data == 'back_to_menu':
        await start(update, context)
    elif data == 'riwayat':
        await show_riwayat(query)
    elif data == 'download_riwayat':
        await download_riwayat(query)

# === Target Menu ===
async def show_target_menu(query):
    keyboard = [
        [InlineKeyboardButton("📝 Atur Target Baru", callback_data='atur_target')],
        [InlineKeyboardButton("📊 Lihat Progress Target", callback_data='lihat_target')],
        [InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data='back_to_menu')]
    ]
    await query.edit_message_text("🎯 Menu Target Nabung", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_text_input(update: Update, context: CallbackContext):
    if not context.user_data.get("awaiting_target_input"):
        return

    try:
        parts = update.message.text.strip().split()
        if len(parts) != 2:
            raise ValueError("Input tidak valid")

        durasi_hari = int(parts[0])
        mulai = datetime.strptime(parts[1], "%Y-%m-%d").date()
        if durasi_hari <= 0 or mulai > date.today() + timedelta(days=365*10):
            raise ValueError("Durasi atau tanggal tidak valid")

        targets = load_target()
        targets[str(update.effective_user.id)] = {
            "mulai": mulai.isoformat(),
            "durasi": durasi_hari
        }
        save_target(targets)

        await update.message.reply_text(f"🎯 Target berhasil disimpan: {durasi_hari} hari mulai {mulai.strftime('%d %b %Y')}")
    except Exception as e:
        await update.message.reply_text("Format salah. Contoh: `365 2025-05-01`", parse_mode="Markdown")

    context.user_data["awaiting_target_input"] = False

async def show_target_custom(query):
    status = load_status()
    targets = load_target()
    user_id = str(query.from_user.id)

    if user_id not in targets:
        await query.edit_message_text("⚠️ Kamu belum mengatur target. Gunakan menu 'Atur Target Baru'.", reply_markup=main_menu())
        return

    mulai = datetime.strptime(targets[user_id]["mulai"], "%Y-%m-%d").date()
    durasi = targets[user_id]["durasi"]

    tanggal_target = [(mulai + timedelta(days=i)).strftime("%d-%b-%Y") for i in range(durasi)]
    total_saved = sum(1 for t in tanggal_target if status.get(t, {}).get("saved", False))
    persen = (total_saved / durasi) * 100
    sisa = durasi - total_saved

    pesan = (
        f"🎯 Progress Target Nabung\n\n"
        f"📅 Mulai: {mulai.strftime('%d %b %Y')}\n"
        f"⏳ Durasi: {durasi} hari\n"
        f"✅ Hari sudah nabung: {total_saved}\n"
        f"📈 Progress: {persen:.2f}%\n"
        f"📆 Hari tersisa: {sisa}\n"
        f"💰 Total terkumpul: Rp{total_saved * NABUNG_PER_HARI:,}"
    )
    await query.edit_message_text(pesan, reply_markup=main_menu())

# === Lain-lain tetap sama === (handle_check_today, tambah_sebelum, show_progress, show_statistik, show_riwayat, download_riwayat, tambah_nabung)

# === Main ===
def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("tambah", tambah_nabung))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    application.run_polling()
    
async def tambah_nabung(update: Update, context: CallbackContext):
    today = today_key()
    status = load_status()

    if today in status and status[today].get("saved"):
        await update.message.reply_text("⚠️ Kamu sudah menabung hari ini.")
    else:
        status[today] = {"saved": True}
        save_status(status)

        streak = hitung_beruntun(status)
        await update.message.reply_text(
            f"✅ Nabung hari ini berhasil dicatat!\n"
            f"🔥 Kamu sudah menabung {streak} hari berturut-turut!"
        )

if __name__ == '__main__':
    main()
