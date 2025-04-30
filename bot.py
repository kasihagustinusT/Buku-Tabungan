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

# Konfigurasi
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
STATUS_FILE = "status.json"
TARGET_FILE = "target.json"
DEFAULT_NABUNG_PER_HARI = 20000

# ==================== FUNGSI BANTU ====================
def load_status() -> dict:
    """Memuat status tabungan dari file JSON"""
    try:
        with open(STATUS_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_status(status: dict) -> None:
    """Menyimpan status tabungan ke file JSON"""
    with open(STATUS_FILE, "w", encoding='utf-8') as f:
        json.dump(status, f, indent=2, ensure_ascii=False)

def today_key() -> str:
    """Mengembalikan string tanggal hari ini dalam format DD-Mon-YYYY"""
    return date.today().strftime("%d-%b-%Y")

def hitung_beruntun(status: dict) -> int:
    """Menghitung streak menabung berturut-turut"""
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
        logger.error(f"Error menghitung streak: {e}")
        return 0

def load_target() -> dict:
    """Memuat target tabungan dari file JSON"""
    try:
        with open(TARGET_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_target(data: dict) -> None:
    """Menyimpan target tabungan ke file JSON"""
    with open(TARGET_FILE, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def buat_progress_bar(persen: float, panjang: int = 10) -> str:
    """Membuat progress bar visual"""
    persen = max(0, min(persen, 1.0))  # Pastikan persen antara 0-1
    blok_terisi = int(round(persen * panjang))
    return "▓" * blok_terisi + "░" * (panjang - blok_terisi)

def format_rupiah(nominal: int) -> str:
    """Format nominal menjadi string Rupiah"""
    return f"Rp{nominal:,}".replace(",", ".")

# ==================== MENU UTAMA ====================
def main_menu() -> InlineKeyboardMarkup:
    """Membuat menu utama dengan inline keyboard"""
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

# ==================== COMMAND HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk command /start"""
    text = (
        "💰 *Buku Tabungan Digital* 💰\n\n"
        "Selamat datang di bot tabungan harian!\n"
        "Saya akan membantu Anda mencatat dan melacak tabungan harian Anda.\n\n"
        "Gunakan menu di bawah untuk mulai:"
    )
    
    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu(), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=main_menu(), parse_mode="Markdown")

# ==================== BUTTON HANDLERS ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk semua callback query dari inline keyboard"""
    query = update.callback_query
    await query.answer()
    data = query.data

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
    elif data == 'back_to_menu':
        await start(update, context)
    elif data == 'riwayat':
        await show_riwayat(query, context)
    elif data == 'download_riwayat':
        await download_riwayat(query, context)
    else:
        await query.edit_message_text("Perintah tidak dikenali. Silakan coba lagi.", reply_markup=main_menu())

# ==================== FUNGSI TABUNGAN ====================
async def handle_check_today(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mencatat tabungan hari ini"""
    status = load_status()
    today = today_key()
    
    if today in status and status[today].get("saved"):
        await query.edit_message_text("⚠️ Kamu sudah menabung hari ini.", reply_markup=main_menu())
        return
    
    status[today] = {"saved": True, "amount": DEFAULT_NABUNG_PER_HARI}
    save_status(status)
    
    streak = hitung_beruntun(status)
    total_hari = sum(1 for v in status.values() if v.get("saved"))
    total_uang = total_hari * DEFAULT_NABUNG_PER_HARI
    
    response = (
        f"✅ *Nabung hari ini berhasil dicatat!*\n\n"
        f"🔥 *Streak:* {streak} hari berturut-turut\n"
        f"📊 *Total:* {total_hari} hari ({format_rupiah(total_uang)})\n\n"
        f"Teruskan kebiasaan baik ini!"
    )
    
    await query.edit_message_text(response, reply_markup=main_menu(), parse_mode="Markdown")

async def tambah_sebelum(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mencatat tabungan hari sebelumnya"""
    status = load_status()
    kemarin = (date.today() - timedelta(days=1)).strftime("%d-%b-%Y")
    
    if kemarin in status and status[kemarin].get("saved"):
        await query.edit_message_text("⚠️ Kamu sudah menabung kemarin.", reply_markup=main_menu())
        return
    
    status[kemarin] = {"saved": True, "amount": DEFAULT_NABUNG_PER_HARI}
    save_status(status)
    
    await query.edit_message_text(
        "✅ *Nabung kemarin berhasil ditambahkan!*",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

async def show_progress(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan progress tabungan"""
    status = load_status()
    total_hari = sum(1 for v in status.values() if v.get("saved"))
    total_uang = total_hari * DEFAULT_NABUNG_PER_HARI
    streak = hitung_beruntun(status)
    
    response = (
        f"📊 *Progress Tabungan*\n\n"
        f"✅ *Hari menabung:* {total_hari}\n"
        f"💰 *Total tabungan:* {format_rupiah(total_uang)}\n"
        f"🔥 *Streak saat ini:* {streak} hari\n\n"
        f"Terus semangat menabung!"
    )
    
    await query.edit_message_text(response, reply_markup=main_menu(), parse_mode="Markdown")

async def show_statistik(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan statistik bulan ini"""
    status = load_status()
    bulan_ini = date.today().strftime("%b-%Y")
    hari_nabung = [k for k, v in status.items() if bulan_ini in k and v.get("saved")]
    total_hari = len(hari_nabung)
    total_uang = total_hari * DEFAULT_NABUNG_PER_HARI
    
    today = date.today()
    first_day = today.replace(day=1)
    days_passed = (today - first_day).days + 1
    persentase = (total_hari / days_passed) * 100 if days_passed > 0 else 0
    
    response = (
        f"📅 *Statistik Bulan {bulan_ini}*\n\n"
        f"📆 *Hari berlalu:* {days_passed}\n"
        f"✅ *Hari nabung:* {total_hari}\n"
        f"💰 *Total:* {format_rupiah(total_uang)}\n"
        f"📈 *Persentase:* {persentase:.1f}%\n\n"
        f"Targetkan {100-persentase:.1f}% lagi untuk menyempurnakan bulan ini!"
    )
    
    await query.edit_message_text(response, reply_markup=main_menu(), parse_mode="Markdown")

async def show_riwayat(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan riwayat tabungan"""
    status = load_status()
    daftar = sorted(
        (k for k, v in status.items() if v.get("saved")), 
        key=lambda x: datetime.strptime(x, "%d-%b-%Y"), 
        reverse=True
    )
    
    if not daftar:
        await query.edit_message_text("Belum ada riwayat menabung.", reply_markup=main_menu())
        return
    
    riwayat_terakhir = daftar[:30]
    total_hari = len(daftar)
    total_uang = total_hari * DEFAULT_NABUNG_PER_HARI
    
    response = (
        f"🗂️ *Riwayat Menabung* (30 terakhir dari {total_hari} hari)\n"
        f"💰 *Total:* {format_rupiah(total_uang)}\n\n" +
        "\n".join(f"✅ {tgl}" for tgl in riwayat_terakhir)
    )
    
    await query.edit_message_text(response, reply_markup=main_menu(), parse_mode="Markdown")

async def download_riwayat(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengirim file CSV riwayat tabungan"""
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
                amount = status[tgl].get("amount", DEFAULT_NABUNG_PER_HARI)
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

# ==================== TARGET HANDLERS ====================
async def show_target_menu(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan menu target"""
    keyboard = [
        [InlineKeyboardButton("📝 Atur Target Baru", callback_data='atur_target')],
        [InlineKeyboardButton("📊 Lihat Progress Target", callback_data='lihat_target')],
        [InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data='back_to_menu')]
    ]
    await query.edit_message_text(
        "🎯 *Menu Target Nabung*\n\nPilih opsi di bawah:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def atur_target_handler(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Meminta input target baru"""
    await query.edit_message_text(
        "📝 *Atur Target Tabungan Baru*\n\n"
        "Silakan kirim dalam format:\n\n"
        "`<durasi_hari> <tanggal_mulai> <jumlah_per_hari>`\n\n"
        "Contoh: `365 2025-05-01 20000`\n\n"
        "Artinya: menabung selama 365 hari mulai 1 Mei 2025 dengan Rp20.000 per hari.",
        parse_mode="Markdown"
    )
    context.user_data["awaiting_target_input"] = True

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Memproses input target baru"""
    if not context.user_data.get("awaiting_target_input"):
        return

    try:
        text = update.message.text.strip()
        parts = text.split()
        
        if len(parts) != 3:
            raise ValueError("Format input harus terdiri dari 3 bagian")
            
        durasi_hari = int(parts[0])
        mulai = datetime.strptime(parts[1], "%Y-%m-%d").date()
        per_hari = int(parts[2])
        
        if durasi_hari <= 0:
            raise ValueError("Durasi harus lebih dari 0 hari")
        if per_hari <= 0:
            raise ValueError("Jumlah per hari harus lebih dari 0")
        if mulai > date.today():
            raise ValueError("Tanggal mulai tidak boleh di masa depan")

        targets = load_target()
        user_id = str(update.effective_user.id)
        
        targets[user_id] = {
            "mulai": mulai.isoformat(),
            "durasi": durasi_hari,
            "per_hari": per_hari,
            "target_total": durasi_hari * per_hari
        }
        
        save_target(targets)
        
        estimasi_selesai = mulai + timedelta(days=durasi_hari)
        
        response = (
            f"🎯 *Target berhasil disimpan!*\n\n"
            f"📅 *Mulai:* {mulai.strftime('%d %b %Y')}\n"
            f"📆 *Selesai:* {estimasi_selesai.strftime('%d %b %Y')}\n"
            f"⏳ *Durasi:* {durasi_hari} hari\n"
            f"💰 *Per Hari:* {format_rupiah(per_hari)}\n"
            f"🎯 *Target Total:* {format_rupiah(durasi_hari * per_hari)}\n\n"
            f"Gunakan menu 'Lihat Progress Target' untuk memantau perkembangan!"
        )
        
        await update.message.reply_text(response, parse_mode="Markdown")
        
    except ValueError as e:
        error_msg = (
            "❌ *Format input tidak valid*\n\n"
            "Pastikan format:\n\n"
            "`<durasi_hari> <tahun-bulan-tanggal> <jumlah_per_hari>`\n\n"
            f"*Error:* {str(e)}\n\n"
            "Contoh: `30 2025-01-01 10000`"
        )
        await update.message.reply_text(error_msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error menyimpan target: {e}")
        await update.message.reply_text(
            "❌ Terjadi kesalahan saat menyimpan target. Silakan coba lagi.",
            parse_mode="Markdown"
        )
    
    context.user_data["awaiting_target_input"] = False

async def show_target_custom(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan progress target"""
    status = load_status()
    targets = load_target()
    user_id = str(query.from_user.id)

    if user_id not in targets:
        await query.edit_message_text(
            "⚠️ Kamu belum mengatur target.\nGunakan menu 'Atur Target Baru' untuk membuat target.",
            reply_markup=main_menu()
        )
        return

    target_data = targets[user_id]
    mulai = datetime.strptime(target_data["mulai"], "%Y-%m-%d").date()
    durasi = target_data["durasi"]
    per_hari = target_data["per_hari"]
    target_total = target_data["target_total"]
    
    estimasi_selesai = mulai + timedelta(days=durasi)
    hari_ini = date.today()
    
    if hari_ini < mulai:
        hari_sudah = 0
        persen = 0.0
    else:
        hari_sudah = min((hari_ini - mulai).days + 1, durasi)
        persen = hari_sudah / durasi
    
    tabungan_seharusnya = per_hari * hari_sudah
    
    tabungan_aktual = 0
    for tgl_str, data in status.items():
        if data.get("saved"):
            tgl = datetime.strptime(tgl_str, "%d-%b-%Y").date()
            if mulai <= tgl <= min(hari_ini, estimasi_selesai - timedelta(days=1)):
                tabungan_aktual += data.get("amount", DEFAULT_NABUNG_PER_HARI)
    
    if tabungan_seharusnya > 0:
        persen_aktual = min(tabungan_aktual / tabungan_seharusnya, 1.0)
    else:
        persen_aktual = 0.0
    
    bar_target = buat_progress_bar(persen)
    bar_aktual = buat_progress_bar(persen_aktual)
    
    response = (
        f"📊 *Progress Target Nabung*\n\n"
        f"📅 *Periode:* {mulai.strftime('%d %b %Y')} - {estimasi_selesai.strftime('%d %b %Y')}\n"
        f"⏳ *Progress Waktu:* {hari_sudah}/{durasi} hari\n"
        f"💰 *Target Harian:* {format_rupiah(per_hari)}\n"
        f"🎯 *Target Total:* {format_rupiah(target_total)}\n\n"
        f"⏱ *Progress Waktu:*\n{bar_target} {persen*100:.1f}%\n\n"
        f"💵 *Tabungan Aktual:* {format_rupiah(tabungan_aktual)}\n"
        f"📈 *Progress Tabungan:*\n{bar_aktual} {persen_aktual*100:.1f}%\n\n"
        f"💪 *Selisih:* {format_rupiah(tabungan_aktual - tabungan_seharusnya)}"
    )
    
    await query.edit_message_text(response, reply_markup=main_menu(), parse_mode="Markdown")

# ==================== MAIN ====================
def main() -> None:
    """Menjalankan bot"""
    application = Application.builder().token(TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))

    # Jalankan bot
    logger.info("Bot sedang berjalan...")
    application.run_polling()

if __name__ == '__main__':
    main()
