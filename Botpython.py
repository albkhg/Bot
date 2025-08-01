import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random

API_TOKEN = "YOUR_BOT_TOKEN"
GROUP_ID = -1002596386909 # Replace with your group ID
ADMIN_ID = 7775019590      # Your Telegram user ID

bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")

# Challenges (same as before)
CHALLENGES = [
    {
        "id": "login_logic",
        "desc": "🔐 Fix the broken login logic (must require BOTH username and password).",
        "code": """```python
def login(username, password):
    if username == "admin" or password == "admin123":
        return True
    return False
```""",
        "options": [
            'username == "admin" or password == "admin123"',  # wrong
            'username == "admin" and password == "admin123"',  # correct
            'username != "admin" and password != "admin123"',  # wrong
            'username == "admin" or password != "admin123"'   # wrong
        ],
        "correct_index": 1
    },
    # Add more challenges as needed...
]

user_stats = {}
active_challenges = {}
new_users_count = 0

@bot.chat_member_handler()
def handle_new_member(event):
    global new_users_count
    new_user = event.new_chat_member.user
    if event.new_chat_member.status == "member":
        new_users_count += 1
        try:
            bot.ban_chat_member(GROUP_ID, new_user.id)
            bot.unban_chat_member(GROUP_ID, new_user.id)
            challenge_idx = random.randint(0, len(CHALLENGES) - 1)
            challenge = CHALLENGES[challenge_idx]
            active_challenges[new_user.id] = challenge_idx
            if new_user.id not in user_stats:
                user_stats[new_user.id] = {'attempts': 0, 'successes': 0, 'failures': 0}
            markup = InlineKeyboardMarkup(row_width=2)
            buttons = []
            for i, option in enumerate(challenge["options"]):
                buttons.append(InlineKeyboardButton(option, callback_data=f"answer_{i}"))
            markup.add(*buttons)
            bot.send_message(
                new_user.id,
                f"👋 *Welcome hacker!*\n\n"
                f"{challenge['desc']}\n\n"
                f"{challenge['code']}\n\n"
                "Select the correct fix from the options below:",
                reply_markup=markup,
                disable_web_page_preview=True
            )
        except Exception as e:
            print(f"[ERROR] Failed to send challenge to {new_user.id}: {e}")

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("answer_"))
def handle_answer(call):
    user_id = call.from_user.id
    choice = int(call.data.split("_")[1])
    if user_id not in active_challenges:
        bot.answer_callback_query(call.id, "Your challenge session expired or no active challenge.")
        return
    challenge_idx = active_challenges[user_id]
    challenge = CHALLENGES[challenge_idx]
    user_stats[user_id]['attempts'] += 1
    if choice == challenge["correct_index"]:
        user_stats[user_id]['successes'] += 1
        try:
            invite = bot.create_chat_invite_link(GROUP_ID, member_limit=1)
            bot.edit_message_text("✅ Correct! Check your private messages for the invite link.",
                                  call.message.chat.id, call.message.message_id)
            bot.send_message(user_id, f"🎉 Congratulations! Here's your private invite link:\n{invite.invite_link}")
        except Exception as e:
            bot.send_message(user_id, "❌ Failed to generate invite link. Contact admin.")
            print(f"[ERROR] Invite link error for {user_id}: {e}")
    else:
        user_stats[user_id]['failures'] += 1
        bot.edit_message_text("❌ Wrong answer. Please try again later.",
                              call.message.chat.id, call.message.message_id)
    del active_challenges[user_id]

@bot.message_handler(commands=['stats'])
def send_stats(msg):
    uid = msg.from_user.id
    stats = user_stats.get(uid)
    if not stats:
        bot.reply_to(msg, "You don't have any recorded attempts yet.")
        return
    reply = (
        f"📊 Your CAPTCHA Stats:\n"
        f"✅ Successes: {stats['successes']}\n"
        f"⚠️ Attempts: {stats['attempts']}\n"
        f"❌ Failures: {stats['failures']}\n"
    )
    bot.reply_to(msg, reply)

# New users counter command and buttons omitted for brevity (use previous code if needed)

# === BROADCAST COMMAND ===
@bot.message_handler(commands=['broadcast'])
def broadcast_message(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.reply_to(msg, "❌ You are not authorized to use this command.")
        return
    args = msg.text.split(' ', 1)
    if len(args) < 2 or not args[1].strip():
        bot.reply_to(msg, "⚠️ Usage: /broadcast Your message here")
        return
    text = args[1].strip()
    sent = 0
    failed = 0
    bot.reply_to(msg, f"📢 Broadcasting message to {len(user_stats)} users...")
    for user_id in user_stats.keys():
        try:
            bot.send_message(user_id, f"📢 *Broadcast message from Admin:*\n\n{text}")
            sent += 1
        except Exception as e:
            failed += 1
            print(f"[ERROR] Failed to send broadcast to {user_id}: {e}")
    bot.send_message(ADMIN_ID, f"📊 Broadcast completed:\n✅ Sent: {sent}\n❌ Failed: {failed}")

print("✅ Bot running with broadcast command...")
bot.infinity_polling()
            for i, option in enumerate(challenge["options"]):
                buttons.append(InlineKeyboardButton(option, callback_data=f"answer_{i}"))
            markup.add(*buttons)
            bot.send_message(
                new_user.id,
                f"👋 *Welcome hacker!*\n\n"
                f"{challenge['desc']}\n\n"
                f"{challenge['code']}\n\n"
                "Select the correct fix from the options below:",
                reply_markup=markup,
                disable_web_page_preview=True
            )
        except Exception as e:
            print(f"[ERROR] Failed to send challenge to {new_user.id}: {e}")

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("answer_"))
def handle_answer(call):
    user_id = call.from_user.id
    choice = int(call.data.split("_")[1])
    if user_id not in active_challenges:
        bot.answer_callback_query(call.id, "Your challenge session expired or no active challenge.")
        return
    challenge_idx = active_challenges[user_id]
    challenge = CHALLENGES[challenge_idx]
    user_stats[user_id]['attempts'] += 1
    if choice == challenge["correct_index"]:
        user_stats[user_id]['successes'] += 1
        try:
            invite = bot.create_chat_invite_link(GROUP_ID, member_limit=1)
            bot.edit_message_text("✅ Correct! Check your private messages for the invite link.",
                                  call.message.chat.id, call.message.message_id)
            bot.send_message(user_id, f"🎉 Congratulations! Here's your private invite link:\n{invite.invite_link}")
        except Exception as e:
            bot.send_message(user_id, "❌ Failed to generate invite link. Contact admin.")
            print(f"[ERROR] Invite link error for {user_id}: {e}")
    else:
        user_stats[user_id]['failures'] += 1
        bot.edit_message_text("❌ Wrong answer. Please try again later.",
                              call.message.chat.id, call.message.message_id)
    del active_challenges[user_id]

@bot.message_handler(commands=['stats'])
def send_stats(msg):
    uid = msg.from_user.id
    stats = user_stats.get(uid)
    if not stats:
        bot.reply_to(msg, "You don't have any recorded attempts yet.")
        return
    reply = (
        f"📊 Your CAPTCHA Stats:\n"
        f"✅ Successes: {stats['successes']}\n"
        f"⚠️ Attempts: {stats['attempts']}\n"
        f"❌ Failures: {stats['failures']}\n"
    )
    bot.reply_to(msg, reply)

# New users counter command and buttons omitted for brevity (use previous code if needed)

# === BROADCAST COMMAND ===
@bot.message_handler(commands=['broadcast'])
def broadcast_message(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.reply_to(msg, "❌ You are not authorized to use this command.")
        return
    args = msg.text.split(' ', 1)
    if len(args) < 2 or not args[1].strip():
        bot.reply_to(msg, "⚠️ Usage: /broadcast Your message here")
        return
    text = args[1].strip()
    sent = 0
    failed = 0
    bot.reply_to(msg, f"📢 Broadcasting message to {len(user_stats)} users...")
    for user_id in user_stats.keys():
        try:
            bot.send_message(user_id, f"📢 *Broadcast message from Admin:*\n\n{text}")
            sent += 1
        except Exception as e:
            failed += 1
            print(f"[ERROR] Failed to send broadcast to {user_id}: {e}")
    bot.send_message(ADMIN_ID, f"📊 Broadcast completed:\n✅ Sent: {sent}\n❌ Failed: {failed}")

print("✅ Bot running with broadcast command...")
bot.infinity_polling()
