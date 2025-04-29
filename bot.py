import os
import json
import csv
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = '7947524305:AAEurXt7P280cv4kFFK4uWohE-eTPW-mZS4'

# Konstanta
START_DATE = datetime(2025, 4, 29)
DAYS = 1095
DAILY_SAVING = 20000
ITEMS_PER_PAGE = 10

# Helper functions
def get_user_file(user_id):
    return f"data/{user_id}.json"

def load_status(user_id):
    if not os.path.exists('data'):
        os.makedirs('data')
    path = get_user_file(user_id)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    else:
        status = {}
        for i in range(DAYS):
            date = (START_DATE + timedelta(days=i)).strftime('%d-%b-%Y')
            status[date] = False
        save_status(user_id, status)
        return status

def save_status(user_id, status):
    path = get_user_file(user_id)
    with open(path, 'w') as f:
        json.dump(status, f, indent=4)

def export_to_csv(user_id, status):
    path = f"data/{user_id}_export.csv"
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Tanggal', 'Status'])
        for date, done in status.items():
            writer.writerow([date, 'Sudah' if done else 'Belum'])
    return path

def get_dates_filtered(status, selected_month=None, selected_year=None):
    dates = list(status.keys())
    filtered = []
    for d in dates:
        date_obj = datetime.strptime(d, '%d-%b-%Y')
        if selected_month and date_obj.strftime('%B') != selected_month:
            continue
        if selected_year and date_obj.year != selected_year:
            continue
        filtered.append(d)
    return filtered

def progress_bar(done, total):
    bar = '█' * int(30 * done // total) + '-' * (30 - int(30 * done // total))
    return f"[{bar}] {done}/{total} hari"

# Bot commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Selamat datang di Buku Tabungan Bot!\n"
        "Gunakan perintah:\n"
        "/status - Cek progress tabungan\n"
        "/centang - Centang/uncentang hari\n"
        "/reset - Reset semua progress\n"
        "/export - Ekspor data ke CSV\n"
        "/filter - Filter berdasarkan bulan/tahun"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    status = load_status(user_id)
    done = sum(1 for d in status if status[d])
    total = len(status)
    total_saved = done * DAILY_SAVING

    await update.message.reply_text(
        f"Progress Nabung:\n{progress_bar(done, total)}\n"
        f"Total tabungan: Rp{total_saved:,}"
    )

async def centang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    status = load_status(user_id)

    # tampilkan 10 hari terakhir
    recent_dates = sorted(status.keys())[-10:]
    keyboard = [
        [InlineKeyboardButton(f"{'✓' if status[date] else '✗'} {date}", callback_data=f"toggle_{date}")]
        for date in recent_dates
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Pilih tanggal untuk centang/uncentang:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    status = load_status(user_id)

    data = query.data
    if data.startswith("toggle_"):
        date = data.replace("toggle_", "")
        if date in status:
            status[date] = not status[date]
            save_status(user_id, status)
            await query.edit_message_text(f"Tanggal {date} diubah menjadi {'✓ Sudah' if status[date] else '✗ Belum'}.")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    status = {}
    for i in range(DAYS):
        date = (START_DATE + timedelta(days=i)).strftime('%d-%b-%Y')
        status[date] = False
    save_status(user_id, status)
    await update.message.reply_text("Semua progress berhasil direset!")

async def export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    status = load_status(user_id)
    path = export_to_csv(user_id, status)
    await update.message.reply_document(document=InputFile(path))

async def filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Maaf, fitur filter bulan/tahun sedang dalam pengembangan.\n"
        "Sementara gunakan /centang untuk melihat daftar terbaru."
    )

# Main app
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("centang", centang))
app.add_handler(CommandHandler("reset", reset))
app.add_handler(CommandHandler("export", export))
app.add_handler(CommandHandler("filter", filter_command))
app.add_handler(CallbackQueryHandler(button))

if __name__ == "__main__":
    app.run_polling()
