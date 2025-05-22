import os
import re
from datetime import datetime, timedelta, date
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# Token da variabile ambiente
TOKEN = os.environ["BOT_TOKEN"]

# Memoria: user_id → lista di (numero, timestamp)
user_data = {}
# Stato temporaneo: user_id → dict con data_inizio, ecc.
user_state = {}

# Estrazione numeri con virgola
def estrai_numeri(testo):
    testo = testo.replace(',', '.')
    return [float(num) for num in re.findall(r'-?\d+(?:\.\d+)?', testo)]

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["🧮 Somma ultimi 30 minuti", "📊 Totale assoluto"],
        ["📅 Somma intervallo personalizzato", "🔄 Reset dati"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Ciao! Mandami numeri o usa i pulsanti:",
        reply_markup=reply_markup
    )

# Salva numeri da testo/caption
async def salva_numeri(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    testo = update.message.caption if update.message.caption else update.message.text
    if not testo:
        return

    numeri = estrai_numeri(testo)
    if not numeri:
        return

    ora = datetime.now()
    user_data.setdefault(user_id, []).extend((n, ora) for n in numeri)
    await update.message.reply_text(f"Salvati: {numeri}")

# /somma con argomenti
async def somma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    now = datetime.now()
    valori = user_data.get(user_id, [])

    if not args:
        await update.message.reply_text("Usa /somma <minuti> oppure /somma da_YYYY-MM-DD a_YYYY-MM-DD")
        return

    if args[0].isdigit():
        minuti = int(args[0])
        t0 = now - timedelta(minutes=minuti)
        somma = sum(val for val, t in valori if t >= t0)
        await update.message.reply_text(f"Somma ultimi {minuti} minuti: {somma}")
        return

    try:
        da = [a for a in args if a.startswith("da_")]
        a = [a for a in args if a.startswith("a_")]
        if da and a:
            t_da = datetime.strptime(da[0][3:], "%Y-%m-%d")
            t_a = datetime.strptime(a[0][2:], "%Y-%m-%d") + timedelta(days=1)
            somma = sum(val for val, t in valori if t_da <= t < t_a)
            await update.message.reply_text(f"Somma dal {t_da.date()} al {(t_a - timedelta(days=1)).date()}: {somma}")
        else:
            raise ValueError
    except:
        await update.message.reply_text("Formato errato. Esempio: /somma da_2025-01-01 a_2025-01-03")

# Menu dei pulsanti
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    testo = update.message.text
    now = datetime.now()
    valori = user_data.get(user_id, [])

    if testo == "🧮 Somma ultimi 30 minuti":
        t0 = now - timedelta(minutes=30)
        somma = sum(val for val, t in valori if t >= t0)
        await update.message.reply_text(f"Somma ultimi 30 minuti: {somma}")

    elif testo == "📊 Totale assoluto":
        somma = sum(val for val, _ in valori)
        await update.message.reply_text(f"Totale salvato: {somma}")

    elif testo == "🔄 Reset dati":
        user_data[user_id] = []
        await update.message.reply_text("Dati azzerati!")

    elif testo == "📅 Somma intervallo personalizzato":
        oggi = date.today()
        btns = [
            [InlineKeyboardButton("🗓️ Oggi", callback_data=f"intervallo:{oggi}:{oggi}")],
            [InlineKeyboardButton("🗓️ Ieri", callback_data=f"intervallo:{oggi - timedelta(days=1)}:{oggi - timedelta(days=1)}")],
            [InlineKeyboardButton("🗓️ Ultimi 3 giorni", callback_data=f"intervallo:{oggi - timedelta(days=2)}:{oggi}")],
        ]
        reply_markup = InlineKeyboardMarkup(btns)
        await update.message.reply_text("Seleziona l'intervallo:", reply_markup=reply_markup)

# Gestione delle date cliccate
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    valori = user_data.get(user_id, [])

    if query.data.startswith("intervallo:"):
        _, da_str, a_str = query.data.split(":")
        t_da = datetime.strptime(da_str, "%Y-%m-%d")
        t_a = datetime.strptime(a_str, "%Y-%m-%d") + timedelta(days=1)
        somma = sum(val for val, t in valori if t_da <= t < t_a)
        await query.edit_message_text(f"Somma dal {da_str} al {a_str}: {somma}")

# Setup bot
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("somma", somma))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(🧮|📊|📅|🔄)"), menu_handler))
app.add_handler(MessageHandler(filters.ALL, salva_numeri))
app.add_handler(CallbackQueryHandler(handle_callback))

app.run_polling()
