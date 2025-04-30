import logging
from datetime import datetime
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.ext import CallbackContext

# Mengonfigurasi logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Token bot Telegram
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

# Helper Functions
def load_target():
    try:
        with open("target.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_target(targets):
    with open("target.json", "w") as file:
        json.dump(targets, file)

def format_rupiah(amount):
    return f"Rp {amount:,.0f}"

def buat_progress_bar(progress):
    bar = "▓" * int(progress * 10) + "░" * (10 - int(progress * 10))
    return bar

def get_user_target(user_id):
    targets = load_target()
    return targets.get(str(user_id)), targets

def main_menu(user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Target Nabung", callback_data="target_menu")],
        [InlineKeyboardButton("❌ Keluar", callback_data="exit")]
    ])

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    await update.message.reply_text(
        "Selamat datang di Bot Buku Tabungan!\n\nSilakan pilih menu di bawah ini:",
        reply_markup=main_menu(user_id)
    )

# Target Menu Functions
async def show_target_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
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
    user_id = query.from_user.id
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
            await update.message.reply_text("💸 Kirim jumlah tabungan per hari (dalam angka, tanpa Rp)\nContoh: 10000")
        except ValueError:
            await update.message.reply_text("❌ Durasi harus berupa angka positif.")
    
    elif step == "per_hari":
        try:
            per_hari = int(update.message.text.strip())
            if per_hari <= 0:
                raise ValueError
            context.user_data["per_hari"] = per_hari

            # Simpan ke file target.json
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
                f"✅ Target berhasil disimpan!\n\n"
                f"🗓️ Mulai: {context.user_data['start_date']}\n"
                f"📆 Durasi: {context.user_data['duration']} hari\n"
                f"💸 Per hari: {format_rupiah(per_hari)}\n"
                f"🎯 Estimasi total: {format_rupiah(total)}\n"
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

# Main function to run the bot
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, atur_target_proses))

    logger.info("Bot berjalan...")
    application.run_polling()

if __name__ == "__main__":
    main()
