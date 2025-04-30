import logging
import json
import os
import csv
import calendar
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

def create_calendar(year=None, month=None):
    now = datetime.now()
    if year is None: year = now.year
    if month is None: month = now.month
    
    keyboard = []
    # Header with month and year
    keyboard.append([InlineKeyboardButton(f"{calendar.month_name[month]} {year}", callback_data="ignore")])
    
    # Week days
    keyboard.append([InlineKeyboardButton(day, callback_data="ignore") for day in ["M", "S", "S", "R", "K", "J", "S"]])
    
    # Dates
    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="ignore"))
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                row.append(InlineKeyboardButton(str(day), callback_data=f"calendar_day_{date_str}"))
        keyboard.append(row)
    
    # Month navigation
    prev_year, prev_month = (year-1, 12) if month == 1 else (year, month-1)
    next_year, next_month = (year+1, 1) if month == 12 else (year, month+1)
    
    keyboard.append([
        InlineKeyboardButton("<", callback_data=f"calendar_change_{prev_year}_{prev_month}"),
        InlineKeyboardButton(">", callback_data=f"calendar_change_{next_year}_{next_month}")
    ])
    
    return InlineKeyboardMarkup(keyboard)

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

def target_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📝 Atur Target Baru", callback_data='atur_target')],
        [InlineKeyboardButton("📊 Lihat Progress Target", callback_data='lihat_target')],
        [InlineKeyboardButton("🔄 Reset Target", callback_data='reset_target')],
        [InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data='back_to_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    target, _ = get_user_target(user_id)
    
    text = "💰 *Buku Tabungan Digital* 💰"
    
    if target:
        text += f"\n\nTarget harian Anda: {format_rupiah(target['per_hari'])}"
        text += "\nSilakan pilih menu di bawah:"
        
        if update.message:
            await update.message.reply_text(text, reply_markup=main_menu(user_id), parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text, reply_markup=main_menu(user_id), parse_mode="Markdown")
    else:
        text += "\n\nAnda belum memiliki target tabungan."
        if update.message:
            await update.message.reply_text(text, parse_mode="Markdown")
            await show_target_menu(update, context)
        elif update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text, parse_mode="Markdown")
            await show_target_menu(update, context)

# Button Handlers
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == 'check_today':
        await handle_check_today(query, context)
    elif data == 'tambah_sebelum':
        await tambah_sebelum(query, context)
    elif data == 'progress':
        await show_progress(query, context)
    elif data == 'statistik':
        await show_statistik(query, context)
    elif data == 'target_menu':
        await show_target_menu(query, context)
    elif data == 'atur_target':
        await atur_target_handler(query, context)
    elif data == 'lihat_target':
        await show_target_custom(query, context)
    elif data == 'reset_target':
        await reset_target_handler(query, context)
    elif data == 'back_to_menu':
        await start(update, context)
    elif data == 'riwayat':
        await show_riwayat(query, context)
    elif data == 'download_riwayat':
        await download_riwayat(query, context)
    else:
        await query.edit_message_text("Perintah tidak dikenali. Silakan coba lagi.", reply_markup=main_menu(user_id))

# Calendar Handlers
async def calendar_handler(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = query.data
    
    if data.startswith("calendar_change_"):
        _, _, year, month = data.split('_')
        await query.edit_message_reply_markup(
            reply_markup=create_calendar(int(year), int(month)))
    
    elif data.startswith("calendar_day_"):
        date_str = data.split('_')[-1]
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        if selected_date < date.today():
            await query.answer("Tanggal tidak boleh di masa lalu", show_alert=True)
            return
        
        context.user_data["setting_target"] = {
            "step": "daily_amount",
            "data": {
                "start_date": date_str,
                "duration": context.user_data["setting_target"]["data"]["duration"]
            }
        }
        
        await query.edit_message_text(
            f"📅 Tanggal mulai: {selected_date.strftime('%d %b %Y')}\n\n"
            "Masukkan jumlah tabungan per hari (contoh: 20000):"
        )

# Input Handlers
async def handle_target_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get("setting_target") or context.user_data["setting_target"].get("step") != "duration":
        return
    
    try:
        duration = int(update.message.text.strip())
        if duration <= 0:
            raise ValueError
        
        context.user_data["setting_target"] = {
            "step": "start_date",
            "data": {
                "duration": duration
            }
        }
        
        await update.message.reply_text(
            "Pilih tanggal mulai menabung:",
            reply_markup=create_calendar()
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Durasi harus berupa angka positif. Silakan coba lagi.\n"
            "Contoh: 365"
        )

async def handle_daily_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get("setting_target") or context.user_data["setting_target"].get("step") != "daily_amount":
        return
    
    try:
        amount = int(update.message.text.strip())
        if amount <= 0:
            raise ValueError
        
        target_data = context.user_data["setting_target"]["data"]
        duration = target_data["duration"]
        start_date = target_data["start_date"]
        
        # Save target
        targets = load_target()
        user_id = str(update.effective_user.id)
        
        targets[user_id] = {
            "mulai": start_date,
            "durasi": duration,
            "per_hari": amount,
            "target_total": duration * amount
        }
        save_target(targets)
        
        # Clear temporary data
        del context.user_data["setting_target"]
        
        # Show confirmation and redirect to main menu
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        estimasi_selesai = start_date_obj + timedelta(days=duration)
        
        await update.message.reply_text(
            f"🎯 *Target berhasil disimpan!*\n\n"
            f"📅 Mulai: {start_date_obj.strftime('%d %b %Y')}\n"
            f"📆 Selesai: {estimasi_selesai.strftime('%d %b %Y')}\n"
            f"⏳ Durasi: {duration} hari\n"
            f"💰 Per Hari: {format_rupiah(amount)}\n"
            f"🎯 Target Total: {format_rupiah(duration * amount)}\n\n"
            f"Silakan mulai menabung sekarang!",
            parse_mode="Markdown"
        )
        
        # Redirect to main menu
        await start(update, context)
        
    except ValueError:
        await update.message.reply_text(
            "❌ Jumlah harus berupa angka positif. Silakan coba lagi.\n"
            "Contoh: 20000"
        )

# Target Handlers
async def atur_target_handler(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["setting_target"] = {
        "step": "duration",
        "data": {}
    }
    await query.edit_message_text(
        "📝 *Atur Target Tabungan Baru*\n\n"
        "Masukkan durasi menabung dalam hari (contoh: 365):",
        parse_mode="Markdown"
    )

async def show_target_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if isinstance(update, CallbackQuery):
        query = update
        user_id = query.from_user.id
    else:
        user_id = update.effective_user.id
    
    target, _ = get_user_target(user_id)
    
    text = "🎯 *Menu Target Nabung*"
    if target:
        mulai = datetime.strptime(target['mulai'], "%Y-%m-%d").date()
        text += f"\n\n📅 Mulai: {mulai.strftime('%d %b %Y')}"
        text += f"\n💰 Target Harian: {format_rupiah(target['per_hari'])}"
        text += f"\n🎯 Total Target: {format_rupiah(target['target_total'])}"
    
    reply_markup = target_menu_keyboard()
    
    if isinstance(update, CallbackQuery):
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def reset_target_handler(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = query.from_user.id
    targets = load_target()
    
    if str(user_id) in targets:
        del targets[str(user_id)]
        save_target(targets)
    
    await query.edit_message_text(
        "✅ Target tabungan telah direset.\n\n"
        "Silakan atur target baru untuk melanjutkan.",
        parse_mode="Markdown"
    )
    await show_target_menu(query, context)

async def show_target_custom(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = query.from_user.id
    target, targets = get_user_target(user_id)

    if not target:
        await query.edit_message_text(
            "⚠️ Kamu belum mengatur target.\nGunakan menu 'Atur Target Baru' untuk membuat target.",
            reply_markup=main_menu(user_id)
        )
        return

    mulai = datetime.strptime(target["mulai"], "%Y-%m-%d").date()
    durasi = target["durasi"]
    per_hari = target["per_hari"]
    target_total = target["target_total"]
    
    estimasi_selesai = mulai + timedelta(days=durasi)
    hari_ini = date.today()
    
    if hari_ini < mulai:
        hari_sudah = 0
        persen_waktu = 0.0
    else:
        hari_sudah = min((hari_ini - mulai).days + 1, durasi)
        persen_waktu = hari_sudah / durasi
    
    status = load_status()
    tabungan_aktual = 0
    for tgl_str, data in status.items():
        if data.get("saved"):
            tgl = datetime.strptime(tgl_str, "%d-%b-%Y").date()
            if mulai <= tgl <= min(hari_ini, estimasi_selesai - timedelta(days=1)):
                tabungan_aktual += data.get("amount", 0)
    
    persen_tabungan = tabungan_aktual / target_total if target_total > 0 else 0
    
    bar_waktu = buat_progress_bar(persen_waktu)
    bar_tabungan = buat_progress_bar(persen_tabungan)
    
    response = (
        f"📊 *Progress Target Nabung*\n\n"
        f"📅 *Periode:* {mulai.strftime('%d %b %Y')} - {estimasi_selesai.strftime('%d %b %Y')}\n"
        f"⏳ *Progress Waktu:* {hari_sudah}/{durasi} hari\n"
        f"💰 *Target Harian:* {format_rupiah(per_hari)}\n"
        f"🎯 *Target Total:* {format_rupiah(target_total)}\n\n"
        f"⏱ *Progress Waktu:*\n{bar_waktu} {persen_waktu*100:.1f}%\n\n"
        f"💵 *Tabungan Aktual:* {format_rupiah(tabungan_aktual)}\n"
        f"📈 *Progress Tabungan:*\n{bar_tabungan} {persen_tabungan*100:.1f}%"
    )
    
    await query.edit_message_text(
        response, 
        reply_markup=target_menu_keyboard(),
        parse_mode="Markdown"
    )

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

async def show_statistik(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = query.from_user.id
    status = load_status()
    bulan_ini = date.today().strftime("%b-%Y")
    hari_nabung = [k for k, v in status.items() if bulan_ini in k and v.get("saved")]
    total_hari = len(hari_nabung)
    total_uang = sum(v.get("amount", 0) for k, v in status.items() if bulan_ini in k and v.get("saved"))
    
    today = date.today()
    first_day = today.replace(day=1)
    days_passed = (today - first_day).days + 1
    persentase = (total_hari / days_passed) * 100 if days_passed > 0 else 0
    
    target, _ = get_user_target(user_id)
    if target:
        target_text = f"\n🎯 Target Harian: {format_rupiah(target['per_hari'])}"
    else:
        target_text = ""
    
    response = (
        f"📅 *Statistik Bulan {bulan_ini}*{target_text}\n\n"
        f"📆 Hari berlalu: {days_passed}\n"
        f"✅ Hari nabung: {total_hari}\n"
        f"💰 Total: {format_rupiah(total_uang)}\n"
        f"📈 Persentase: {persentase:.1f}%"
    )
    
    await query.edit_message_text(response, reply_markup=main_menu(user_id), parse_mode="Markdown")

async def show_riwayat(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = query.from_user.id
    status = load_status()
    daftar = sorted(
        (k for k, v in status.items() if v.get("saved")), 
        key=lambda x: datetime.strptime(x, "%d-%b-%Y"), 
        reverse=True
    )
    
    if not daftar:
        await query.edit_message_text("Belum ada riwayat menabung.", reply_markup=main_menu(user_id))
        return
    
    riwayat_terakhir = daftar[:30]
    total_hari = len(daftar)
    total_uang = sum(v.get("amount", 0) for v in status.values() if v.get("saved"))
    
    target, _ = get_user_target(user_id)
    if target:
        target_text = f"\n🎯 Target Harian: {format_rupiah(target['per_hari'])}"
    else:
        target_text = ""
    
    response = (
        f"🗂️ *Riwayat Menabung* (30 terakhir dari {total_hari} hari){target_text}\n"
        f"💰 Total: {format_rupiah(total_uang)}\n\n" +
        "\n".join(f"✅ {tgl} - {format_rupiah(status[tgl].get('amount', 0))}" for tgl in riwayat_terakhir)
    )
    
    await query.edit_message_text(response, reply_markup=main_menu(user_id), parse_mode="Markdown")

async def download_riwayat(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = query.from_user.id
    status = load_status()
    
    sorted_dates = sorted(
        (k for k, v in status.items() if v.get("saved")),
        key=lambda x: datetime.strptime(x, "%d-%b-%Y")
    )
    
    temp_file = "riwayat_tabungan.csv"
    try:
        with open(temp_file, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Tanggal", "Menabung", "Jumlah"])
            for tgl in sorted_dates:
                amount = status[tgl].get("amount", 0)
                writer.writerow([tgl, "Ya", format_rupiah(amount)])
        
        with open(temp_file, "rb") as f:
            await query.message.reply_document(
                document=InputFile(f, filename="riwayat_tabungan.csv"),
                caption="📊 Berikut riwayat tabungan Anda"
            )
    except Exception as e:
        logger.error(f"Gagal membuat file riwayat: {e}")
        await query.message.reply_text("❌ Maaf, gagal membuat file riwayat.")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

# Main Application
def main() -> None:
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CallbackQueryHandler(calendar_handler, pattern="^calendar_"))
    
    # Message handlers with priority
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^\d+$'), handle_target_duration))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^\d+$'), handle_daily_amount))

    logger.info("Bot sedang berjalan...")
    application.run_polling()

if __name__ == '__main__':
    main()
