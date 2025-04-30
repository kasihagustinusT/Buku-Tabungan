import json
import logging
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# Token Telegram Anda
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

# Inisialisasi logger
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Helper
def format_rupiah(amount: int) -> str:
    return f"Rp{amount:,.0f}".replace(",", ".")

def buat_progress_bar(progress: float, length: int = 10) -> str:
    filled_length = int(length * progress)
    bar = "▓" * filled_length + "░" * (length - filled_length)
    return bar

def main_menu(user_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📥 Catat Tabungan", callback_data="catat_tabungan")],
        [InlineKeyboardButton("🎯 Target Nabung", callback_data="target_menu")],
        [InlineKeyboardButton("📊 Lihat Statistik", callback_data="statistik")],
    ]
    return InlineKeyboardMarkup(keyboard)

# File handler
def load_status() -> dict:
    try:
        with open("status.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_status(data: dict):
    with open("status.json", "w") as f:
        json.dump(data, f)

def load_target() -> dict:
    try:
        with open("target.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_target(data: dict):
    with open("target.json", "w") as f:
        json.dump(data, f)

def get_user_target(user_id: int):
    data = load_target()
    return data.get(str(user_id)), data

# Command Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = f"Selamat datang di *Buku Tabungan*, {update.effective_user.first_name}!"
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu(user_id))

# Callback Handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "target_menu":
        await show_target_menu(query, context)
    elif data == "atur_target":
        await atur_target_handler(query, context)
    elif data == "lihat_target":
        await show_target_custom(query, context)
    elif data == "reset_target":
        await reset_target_handler(query, context)

# Target Menu Functions
async def show_target_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("➕ Atur Target Baru", callback_data='atur_target')],
        [InlineKeyboardButton("📄 Lihat Target", callback_data='lihat_target')],
        [InlineKeyboardButton("❌ Reset Target", callback_data='reset_target')],
        [InlineKeyboardButton("🔙 Kembali", callback_data='back_to_menu')]
    ]
    text = "*🎯 Menu Target Nabung*\n\nKelola target tabunganmu di sini:"
    if isinstance(update, CallbackQuery):
        await update.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def atur_target_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update if isinstance(update, CallbackQuery) else update.callback_query
    context.user_data["target_step"] = "tanggal_mulai"
    await query.edit_message_text(
        "🗓️ Kirim tanggal mulai (format: YYYY-MM-DD)\nContoh: 2025-05-01",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="target_menu")]])
    )

async def atur_target_proses(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    step = context.user_data.get("target_step")

    if step == "tanggal_mulai":
        try:
            start_date = datetime.strptime(update.message.text.strip(), "%Y-%m-%d").date()
            context.user_data["start_date"] = start_date
            context.user_data["target_step"] = "durasi"
            await update.message.reply_text("📆 Kirim durasi menabung (dalam hari)\nContoh: 90")
        except ValueError:
            await update.message.reply_text("❌ Format tanggal tidak valid. Gunakan YYYY-MM-DD")

    elif step == "durasi":
        try:
            duration = int(update.message.text.strip())
            if duration <= 0:
                raise ValueError
            context.user_data["duration"] = duration
            context.user_data["target_step"] = "per_hari"
            await update.message.reply_text("💸 Kirim jumlah tabungan per hari (tanpa Rp)\nContoh: 10000")
        except ValueError:
            await update.message.reply_text("❌ Durasi harus berupa angka positif.")

    elif step == "per_hari":
        try:
            per_hari = int(update.message.text.strip())
            if per_hari <= 0:
                raise ValueError
            context.user_data["per_hari"] = per_hari

            # Simpan target
            targets = load_target()
            total = per_hari * context.user_data["duration"]
            targets[str(user_id)] = {
                "start_date": context.user_data["start_date"].isoformat(),
                "duration": context.user_data["duration"],
                "per_hari": per_hari,
                "total_target": total
            }
            save_target(targets)

            bar = buat_progress_bar(0)
            await update.message.reply_text(
                f"✅ Target disimpan!\n\n"
                f"🗓️ Mulai: {context.user_data['start_date']}\n"
                f"📆 Durasi: {context.user_data['duration']} hari\n"
                f"💸 Per hari: {format_rupiah(per_hari)}\n"
                f"🎯 Total: {format_rupiah(total)}\n"
                f"Progress: {bar}",
                reply_markup=main_menu(user_id)
            )
            context.user_data.clear()
        except ValueError:
            await update.message.reply_text("❌ Jumlah per hari harus berupa angka positif.")

async def show_target_custom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update if isinstance(update, CallbackQuery) else update.callback_query
    user_id = query.from_user.id
    target, _ = get_user_target(user_id)

    if not target:
        await query.edit_message_text("⚠️ Belum ada target tersimpan.", reply_markup=main_menu(user_id))
        return

    saved = load_status()
    jumlah_saved = sum(1 for v in saved.values() if v.get("saved"))
    progress = jumlah_saved / target["duration"]
    bar = buat_progress_bar(progress)

    await query.edit_message_text(
        f"🎯 *Target Nabung*\n\n"
        f"🗓️ Mulai: {target['start_date']}\n"
        f"📆 Durasi: {target['duration']} hari\n"
        f"💸 Per hari: {format_rupiah(target['per_hari'])}\n"
        f"🎯 Total target: {format_rupiah(target['total_target'])}\n"
        f"📊 Progress: {bar} ({jumlah_saved}/{target['duration']} hari)",
        parse_mode="Markdown",
        reply_markup=main_menu(user_id)
    )

async def reset_target_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update if isinstance(update, CallbackQuery) else update.callback_query
    user_id = query.from_user.id
    targets = load_target()

    if str(user_id) in targets:
        del targets[str(user_id)]
        save_target(targets)
        await query.edit_message_text("✅ Target berhasil dihapus.", reply_markup=main_menu(user_id))
    else:
        await query.edit_message_text("⚠️ Tidak ada target untuk dihapus.", reply_markup=main_menu(user_id))

# Fungsi Main
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, atur_target_proses))

    logger.info("Bot berjalan...")
    application.run_polling()

if __name__ == "__main__":
    main()
