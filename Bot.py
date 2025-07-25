import logging
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    CallbackContext,
    MessageHandler,
    Filters,
)

# ----------- Konfigurimet -----------

TOKEN = '7717027386:AAF8Y4c8Oln8yUdcKV8XlTZRtSBS1ICqeMM'
ADMIN_USERNAME = 'user9admin'
USDT_WALLET = 'TSwUt8EZ8taiT1TgCaxPVMdXNjPKRsU6vh'
REFERRAL_POINTS = 1

# ----------- Setup logging -----------

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ----------- Lidhja me DB -----------

conn = sqlite3.connect('shop_bot.db', check_same_thread=False)
cursor = conn.cursor()

# ----------- Krijimi i tabelave -----------

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance REAL DEFAULT 0,
    referral_code TEXT,
    referred_by INTEGER,
    join_date TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    price REAL,
    file_id TEXT,
    description TEXT,
    added_date TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS purchases (
    purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    product_id INTEGER,
    purchase_date TEXT,
    FOREIGN KEY(user_id) REFERENCES users(user_id),
    FOREIGN KEY(product_id) REFERENCES products(product_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS deposits (
    deposit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    tx_hash TEXT,
    status TEXT DEFAULT 'pending',
    deposit_date TEXT,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS referrals (
    referral_id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER,
    referred_id INTEGER,
    points_awarded INTEGER DEFAULT 0,
    referral_date TEXT,
    FOREIGN KEY(referrer_id) REFERENCES users(user_id),
    FOREIGN KEY(referred_id) REFERENCES users(user_id)
)
''')

conn.commit()

# ----------- Funksione ndihmëse -----------

def get_user(user_id):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    return cursor.fetchone()

def create_user(user_id, username, referral_code=None):
    if get_user(user_id):
        return None  # User ekziston

    referred_by = None
    if referral_code and referral_code.startswith('ref'):
        try:
            ref_id = int(referral_code[3:])
            if get_user(ref_id):
                referred_by = ref_id
        except:
            referred_by = None

    cursor.execute('''
        INSERT INTO users (user_id, username, balance, referral_code, referred_by, join_date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, username, 0, f'ref{user_id}', referred_by, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()

    if referred_by:
        # Jep pikë referral-it
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (REFERRAL_POINTS, referred_by))
        cursor.execute('''
            INSERT INTO referrals (referrer_id, referred_id, points_awarded, referral_date)
            VALUES (?, ?, ?, ?)
        ''', (referred_by, user_id, REFERRAL_POINTS, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        return f"🎉 Faleminderit që u regjistruat përmes linkut të referimit! Përdoruesi {referred_by} fitoi {REFERRAL_POINTS} pikë."

    return None

def get_products():
    cursor.execute('SELECT product_id, name, price FROM products ORDER BY product_id DESC')
    return cursor.fetchall()

def get_product(product_id):
    cursor.execute('SELECT * FROM products WHERE product_id = ?', (product_id,))
    return cursor.fetchone()

def add_product(name, price, file_id, description):
    cursor.execute('''
        INSERT INTO products (name, price, file_id, description, added_date)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, price, file_id, description, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()

def make_purchase(user_id, product_id):
    product = get_product(product_id)
    user = get_user(user_id)

    if not product:
        return "Produkti nuk u gjet."
    if not user:
        return "Përdoruesi nuk u gjet."

    price = product[2]  # price në rreshtin e produktit
    balance = user[2]   # balance në rreshtin e përdoruesit

    if balance < price:
        return "Saldoja e pamjaftueshme."

    # Zbrit nga balanca
    cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (price, user_id))
    # Regjistro blerjen
    cursor.execute('''
        INSERT INTO purchases (user_id, product_id, purchase_date)
        VALUES (?, ?, ?)
    ''', (user_id, product_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()

    return product[3]  # file_id për dërgim

def record_deposit(user_id, amount, tx_hash):
    cursor.execute('''
        INSERT INTO deposits (user_id, amount, tx_hash, deposit_date)
        VALUES (?, ?, ?, ?)
    ''', (user_id, amount, tx_hash, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()

def get_stats():
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM purchases')
    total_purchases = cursor.fetchone()[0]

    cursor.execute('SELECT COALESCE(SUM(points_awarded), 0) FROM referrals')
    total_points_awarded = cursor.fetchone()[0]

    cursor.execute('SELECT COALESCE(SUM(amount), 0) FROM deposits WHERE status = "approved"')
    total_deposits = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM deposits WHERE status = "pending"')
    pending_deposits = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(DISTINCT user_id) FROM purchases')
    active_users = cursor.fetchone()[0]

    cursor.execute('SELECT AVG(price) FROM products WHERE product_id IN (SELECT product_id FROM purchases)')
    avg_purchase = cursor.fetchone()[0]
    avg_purchase = round(avg_purchase, 2) if avg_purchase else 0

    return {
        "total_users": total_users,
        "total_purchases": total_purchases,
        "total_points_awarded": total_points_awarded,
        "total_deposits": total_deposits,
        "pending_deposits": pending_deposits,
        "active_users": active_users,
        "avg_purchase": avg_purchase,
    }

# ----------- Handlers -----------

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    username = update.effective_user.username or "N/A"

    referral_msg = None
    if context.args:
        referral_code = context.args[0]
        referral_msg = create_user(user_id, username, referral_code)
    else:
        create_user(user_id, username)

    user = get_user(user_id)
    balance = user[2] if user else 0

    message = (
        f"🛍️ Mirësevini @{username}!\n\n"
        f"💰 Saldoja juaj: {balance} pikë\n"
        f"🔗 Linku juaj i referimit: https://t.me/{context.bot.username}?start=ref{user_id}\n\n"
        f"{referral_msg if referral_msg else ''}"
        "Përdorni menunë më poshtë për të vazhduar."
    )

    keyboard = [
        [InlineKeyboardButton("🛒 Produkte", callback_data='products')],
        [InlineKeyboardButton("💰 Saldo", callback_data='balance')],
        [InlineKeyboardButton("💳 Depozitë", callback_data='deposit')],
        [InlineKeyboardButton("📊 Statistika", callback_data='stats')],
        [InlineKeyboardButton("🔗 Referral", callback_data='referral')],
    ]

    if username == ADMIN_USERNAME:
        keyboard.append([InlineKeyboardButton("👑 Panel Admini", callback_data='admin')])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        update.callback_query.edit_message_text(text=message, reply_markup=reply_markup)
    else:
        update.message.reply_text(text=message, reply_markup=reply_markup)

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    user = get_user(user_id)

    # -- Produkte --
    if query.data == 'products':
        products = get_products()
        if not products:
            query.edit_message_text("Nuk ka produkte të disponueshme.")
            return

        keyboard = [
            [InlineKeyboardButton(f"{p[1]} - {p[2]} pikë", callback_data=f'view_product_{p[0]}')]
            for p in products
        ]
        keyboard.append([InlineKeyboardButton("🔙 Mbrapa", callback_data='start')])
        query.edit_message_text("📦 Produktet e disponueshme:", reply_markup=InlineKeyboardMarkup(keyboard))

    # -- Shiko produktin --
    elif query.data.startswith('view_product_'):
        product_id = int(query.data.split('_')[-1])
        product = get_product(product_id)
        if not product:
            query.edit_message_text("Produkti nuk u gjet.")
            return

        text = (
            f"📦 <b>{product[1]}</b>\n"
            f"💰 Çmimi: {product[2]} pikë\n"
            f"📝 Përshkrimi:\n{product[4]}"
        )
        keyboard = [
            [InlineKeyboardButton("🛒 Blej tani", callback_data=f'buy_{product_id}')],
            [InlineKeyboardButton("🔙 Mbrapa", callback_data='products')],
        ]
        query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

    # -- Blej produktin --
    elif query.data.startswith('buy_'):
        product_id = int(query.data.split('_')[-1])
        if not user:
            query.edit_message_text("Nuk u gjet përdoruesi.")
            return
        product = get_product(product_id)
        if not product:
            query.edit_message_text("Produkti nuk u gjet.")
            return

        price = product[2]
        balance = user[2]
        if balance < price:
            keyboard = [
                [InlineKeyboardButton("💳 Depozitë", callback_data='deposit')],
                [InlineKeyboardButton("🔙 Mbrapa", callback_data=f'view_product_{product_id}')],
            ]
            query.edit_message_text(
                "❌ Saldoja nuk mjafton. Ju lutem depozitoni më shumë pika ose fitoni pika të reja.",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        new_balance = balance - price
        keyboard = [
            [InlineKeyboardButton("✅ Konfirmo blerjen", callback_data=f'confirm_buy_{product_id}')],
            [InlineKeyboardButton("❌ Anulo", callback_data=f'view_product_{product_id}')],
        ]
        query.edit_message_text(
            f"⚠️ Konfirmo blerjen\n\nProdukt: {product[1]}\nÇmimi: {price} pika\nSaldo pas blerjes: {new_balance} pika",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    # -- Konfirmo blerjen --
    elif query.data.startswith('confirm_buy_'):
        product_id = int(query.data.split('_')[-1])
        result = make_purchase(user_id, product_id)
        if result in ["Produkti nuk u gjet.", "Përdoruesi nuk u gjet.", "Saldoja e pamjaftueshme."]:
            query.edit_message_text(result)
            return

        file_id = result
        try:
            context.bot.send_document(chat_id=user_id, document=file_id, caption="✅ Blerja u krye me sukses!")
            keyboard = [
                [InlineKeyboardButton("🛒 Produkte të tjera", callback_data='products')],
                [InlineKeyboardButton("🏠 Menu Kryesore", callback_data='start')],
            ]
            query.edit_message_text(
                "🎉 Blerja u krye! Kontrolloni chat-in për produktin tuaj.",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        except Exception as e:
            logger.error(f"Gabim në dërgimin e produktit: {e}")
            query.edit_message_text(
                "⚠️ Gabim në dërgimin e produktit. Ju lutem kontaktoni adminin.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛒 Produkte të tjera", callback_data='products')],
                    [InlineKeyboardButton("🏠 Menu Kryesore", callback_data='start')],
                ]),
            )

    # -- Shiko saldo --
    elif query.data == 'balance':
        if not user:
            query.edit_message_text("Nuk u gjet përdoruesi.")
            return
        balance = user[2]
        query.edit_message_text(
            f"💰 Saldoja juaj aktuale: {balance} pika",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Mbrapa", callback_data='start')]])
        )

    # -- Depozitë --
    elif query.data == 'deposit':
        message = (
            f"💳 Depozitoni USDT (TRC20)\n\n"
            f"Adresa e Wallet-it:\n`{USDT_WALLET}`\n\n"
            "📝 Pas dërgimit, ju lutem dërgoni hash-in e transaksionit tek ky bot.\n\n"
            "Minimumi: 1 USDT = 1 pikë."
        )
        query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Mbrapa", callback_data='start')]])
        )

    # -- Statistika --
    elif query.data == 'stats':
        stats = get_stats()
        text = (
            f"📊 Statistikat e Bot-it:\n\n"
            f"👥 Përdorues total: {stats['total_users']}\n"
            f"🛒 Blerje total: {stats['total_purchases']}\n"
            f"⭐ Pikë referimi total: {stats['total_points_awarded']}\n"
            f"💰 Depozita total: {stats['total_deposits']} pikë\n"
            f"⏳ Depozita në pritje: {stats['pending_deposits']}\n"
            f"👤 Përdorues aktivë: {stats['active_users']}\n"
            f"📈 Vlera mesatare blerjeje: {stats['avg_purchase']} pikë"
        )
        query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Mbrapa", callback_data='start')]]))

    # -- Referral --
    elif query.data == 'referral':
        cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (user_id,))
        total_referrals = cursor.fetchone()[0]
        cursor.execute('SELECT COALESCE(SUM(points_awarded), 0) FROM referrals WHERE referrer_id = ?', (user_id,))
        points_earned = cursor.fetchone()[0]

        text = (
            f"🔗 Programi i Referimeve\n\n"
            f"Fto miqtë dhe fitoni {REFERRAL_POINTS} pikë për secilin!\n\n"
            f"👥 Përdorues të referuar: {total_referrals}\n"
            f"⭐ Pikë të fituara: {points_earned}\n\n"
            f"Linku juaj i referimit:\n"
            f"https://t.me/{context.bot.username}?start=ref{user_id}"
        )
        query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Mbrapa", callback_data='start')]]))

    # -- Paneli Admini --
    elif query.data == 'admin':
        if user and user[1] == ADMIN_USERNAME:
            keyboard = [
                [InlineKeyboardButton("📢 Broadcast", callback_data='broadcast')],
                [InlineKeyboardButton("➕ Shto Produkt", callback_data='add_product')],
                [InlineKeyboardButton("📊 Statistika", callback_data='admin_stats')],
                [InlineKeyboardButton("💵 Depozita në pritje", callback_data='pending_deposits')],
                [InlineKeyboardButton("🔙 Mbrapa", callback_data='start')]
            ]
            query.edit_message_text("👑 Paneli i Adminit\n\nZgjidhni një opsion:", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            query.edit_message_text("⚠️ Access denied.")

    # -- Broadcast (admin) --
    elif query.data == 'broadcast':
        if user and user[1] == ADMIN_USERNAME:
            query.edit_message_text(
                "📢 Dërgo një mesazh për të gjithë përdoruesit.\n\n"
                "Përdor komandën /broadcast ndjekur nga mesazhi."
            )
        else:
            query.edit_message_text("⚠️ Access denied.")

    # -- Statistika admin --
    elif query.data == 'admin_stats':
        if user and user[1] == ADMIN_USERNAME:
            stats = get_stats()
            text = (
                f"📊 Statistika Admini\n\n"
                f"👥 Përdorues total: {stats['total_users']}\n"
                f"🛒 Blerje total: {stats['total_purchases']}\n"
                f"💰 Depozita totale (approved): {stats['total_deposits']}\n"
                f"⏳ Depozita në pritje: {stats['pending_deposits']}\n"
                f"⭐ Pikë referimi total: {stats['total_points_awarded']}"
            )
            query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Mbrapa", callback_data='admin')]]))
        else:
            query.edit_message_text("⚠️ Access denied.")

    # -- Depozita në pritje (admin) --
    elif query.data == 'pending_deposits':
        if user and user[1] == ADMIN_USERNAME:
            cursor.execute('SELECT deposit_id, user_id, amount, tx_hash, deposit_date FROM deposits WHERE status = "pending" ORDER BY deposit_date DESC')
            pending = cursor.fetchall()
            if not pending:
                query.edit_message_text("Nuk ka depozita në pritje.")
                return

            buttons = []
            for d in pending:
                dep_id, u_id, amount, tx, date = d
                buttons.append([
                    InlineKeyboardButton(
                        f"ID:{dep_id} - User:{u_id} - {amount} USDT",
                        callback_data=f'approve_dep_{dep_id}'
                    )
                ])

            buttons.append([InlineKeyboardButton("🔙 Mbrapa", callback_data='admin')])
            query.edit_message_text("📥 Depozita në pritje:", reply_markup=InlineKeyboardMarkup(buttons))
        else:
            query.edit_message_text("⚠️ Access denied.")

    # -- Approve depozitë (admin) --
    elif query.data.startswith('approve_dep_'):
        if user and user[1] == ADMIN_USERNAME:
            dep_id = int(query.data.split('_')[-1])
            cursor.execute('SELECT user_id, amount, status FROM deposits WHERE deposit_id = ?', (dep_id,))
            dep = cursor.fetchone()
            if not dep:
                query.edit_message_text("Depozita nuk u gjet.")
                return
            user_dep_id, amount, status = dep
            if status != 'pending':
                query.edit_message_text("Kjo depozitë është tashmë e përfunduar.")
                return

            # Update status and add balance
            cursor.execute('UPDATE deposits SET status = "approved" WHERE deposit_id = ?', (dep_id,))
            cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_dep_id))
            conn.commit()

            query.edit_message_text(f"✅ Depozita ID {dep_id} u aprovua dhe saldoja u përditësua.")
        else:
            query.edit_message_text("⚠️ Access denied.")

    # -- Menu kryesore --
    elif query.data == 'start':
        start(update, context)

    else:
        query.edit_message_text("Opsion i panjohur.")

# ----------- Komanda per broadcast (admin) -----------

def broadcast(update: Update, context: CallbackContext):
    user = get_user(update.effective_user.id)
    if not user or user[1] != ADMIN_USERNAME:
        update.message.reply_text("⚠️ Nuk keni akses për këtë komandë.")
        return

    if context.args:
        message = ' '.join(context.args)
        cursor.execute('SELECT user_id FROM users')
        users = cursor.fetchall()
        sent_count = 0
        for u in users:
            try:
                context.bot.send_message(chat_id=u[0], text=message)
                sent_count += 1
            except Exception as e:
                logger.error(f"Gabim gjatë dërgimit të broadcast: {e}")
        update.message.reply_text(f"Mesazhi u dërgua tek {sent_count} përdorues.")
    else:
        update.message.reply_text("Përdorni: /broadcast <mesazhi>")

def admin_panel(update: Update, context: CallbackContext):
    user = get_user(update.effective_user.id)
    if user and user[1] == ADMIN_USERNAME:
        keyboard = [
            [InlineKeyboardButton("📢 Broadcast", callback_data='broadcast')],
            [InlineKeyboardButton("➕ Shto Produkt", callback_data='add_product')],
            [InlineKeyboardButton("📊 Statistika", callback_data='admin_stats')],
            [InlineKeyboardButton("💵 Depozita në pritje", callback_data='pending_deposits')],
            [InlineKeyboardButton("🔙 Mbrapa", callback_data='start')]
        ]
        update.message.reply_text("👑 Paneli i Adminit\n\nZgjidhni një opsion:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        update.message.reply_text("⚠️ Nuk keni qasje në panelin e adminit.")

# ----------- Main -----------

def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('broadcast', broadcast, pass_args=True))
    dp.add_handler(CallbackQueryHandler(button_handler))

    updater.start_polling()
    logger.info("Bot është online.")
    updater.idle()

if __name__ == '__main__':
    main()
