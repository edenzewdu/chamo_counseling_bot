import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
import json
import os
from datetime import datetime

# Bot setup and token configuration
API_TOKEN = 'YOUR_BOT_API_TOKEN'  # Replace with your bot's API token
GROUP_CHAT_ID = -100YOUR_GROUP_ID  # Replace with your group chat ID
admins = [ADMIN_ID, ]  # Replace with actual admin IDs

bot = telebot.TeleBot(API_TOKEN)
logging.basicConfig(level=logging.INFO)

# File to store counselor data
COUNSELOR_FILE = 'counselors.json'
SESSION_LOG_DIR = 'sessions'

# Load or initialize counselors
if not os.path.exists(COUNSELOR_FILE):
    with open(COUNSELOR_FILE, 'w') as f:
        json.dump([], f)

# Helper function to load counselors
def load_counselors():
    with open(COUNSELOR_FILE, 'r') as f:
        return json.load(f)

# Helper function to save counselors
def save_counselors(counselors):
    with open(COUNSELOR_FILE, 'w') as f:
        json.dump(counselors, f, indent=4)

# Register a new counselor (admin only)
@bot.message_handler(commands=['register_counselor'])
def register_counselor(message):
    if message.from_user.id not in admins:
        bot.reply_to(message, "You are not authorized to perform this action.")
        return

    msg = bot.reply_to(message, "Enter the counselor's username:")
    bot.register_next_step_handler(msg, save_counselor)

def save_counselor(message):
    username = message.text
    counselors = load_counselors()
    if any(c['username'] == username for c in counselors):
        bot.reply_to(message, f"Counselor @{username} is already registered.")
    else:
        counselors.append({"username": username, "assigned": False})
        save_counselors(counselors)
        bot.reply_to(message, f"Counselor @{username} registered successfully.")

# Delete a counselor (admin only)
@bot.message_handler(commands=['delete_counselor'])
def delete_counselor(message):
    if message.from_user.id not in admins:
        bot.reply_to(message, "You are not authorized to perform this action.")
        return

    msg = bot.reply_to(message, "Enter the username of the counselor to delete:")
    bot.register_next_step_handler(msg, remove_counselor)

def remove_counselor(message):
    username = message.text
    counselors = load_counselors()
    counselors = [c for c in counselors if c['username'] != username]
    save_counselors(counselors)
    bot.reply_to(message, f"Counselor @{username} has been removed.")

# Start a one-on-one counseling session
@bot.message_handler(commands=['request_counseling'])
def request_counseling(message):
    user_id = message.from_user.id
    anonymous_name = f"User_{user_id}"

    # Assign the first available counselor
    counselors = load_counselors()
    available_counselor = next((c for c in counselors if not c['assigned']), None)

    if available_counselor:
        available_counselor['assigned'] = True
        save_counselors(counselors)
        bot.reply_to(message, f"You've been assigned to counselor @{available_counselor['username']}.")
        
        # Notify admin
        for admin_id in admins:
            bot.send_message(admin_id, f"{anonymous_name} has been assigned to counselor @{available_counselor['username']}.")

        # Start session logging
        session_id = f"{anonymous_name}_{available_counselor['username']}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        start_session(user_id, available_counselor['username'], session_id)
    else:
        bot.reply_to(message, "No counselors are currently available. Please try again later.")

# Start and save a session
def start_session(user_id, counselor_username, session_id):
    if not os.path.exists(SESSION_LOG_DIR):
        os.makedirs(SESSION_LOG_DIR)

    session_file = os.path.join(SESSION_LOG_DIR, f"{session_id}.txt")
    with open(session_file, 'w') as f:
        f.write(f"Session started between {user_id} and counselor @{counselor_username}\n")

    bot.send_message(user_id, "You are now in a session with your counselor. Please start sharing.")

    # Track the session
    user_data[user_id] = {'counselor': counselor_username, 'session_file': session_file}

# Log user messages to session file
@bot.message_handler(func=lambda message: message.chat.id in user_data)
def log_session_message(message):
    user_id = message.chat.id
    session_info = user_data[user_id]
    session_file = session_info['session_file']

    with open(session_file, 'a') as f:
        f.write(f"{message.text}\n")

    bot.send_message(user_id, "Message received by counselor.")

# Request counselor change
@bot.message_handler(commands=['change_counselor'])
def request_change_counselor(message):
    user_id = message.from_user.id
    anonymous_name = f"User_{user_id}"

    if user_id in user_data:
        current_counselor = user_data[user_id]['counselor']
        bot.send_message(user_id, "Request sent to admin for a new counselor assignment.")
        
        # Notify admin for reassignment approval
        for admin_id in admins:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("Approve Change", callback_data=f"approve_change_{user_id}"))
            bot.send_message(admin_id, f"{anonymous_name} has requested a new counselor instead of @{current_counselor}.", reply_markup=markup)
    else:
        bot.reply_to(message, "You are not currently in a session.")

# Admin approval for counselor change
@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_change_"))
def approve_counselor_change(call):
    user_id = int(call.data.split("_")[2])
    anonymous_name = f"User_{user_id}"
    current_counselor = user_data[user_id]['counselor']

    # Make current counselor available
    counselors = load_counselors()
    for c in counselors:
        if c['username'] == current_counselor:
            c['assigned'] = False
            break
    save_counselors(counselors)

    # Reassign new counselor
    available_counselor = next((c for c in counselors if not c['assigned']), None)
    if available_counselor:
        available_counselor['assigned'] = True
        save_counselors(counselors)

        # Update session information
        user_data[user_id]['counselor'] = available_counselor['username']
        bot.send_message(user_id, f"You've been reassigned to counselor @{available_counselor['username']}.")
        
        # Notify admin
        bot.send_message(call.message.chat.id, f"{anonymous_name} has been reassigned to counselor @{available_counselor['username']}.")
    else:
        bot.send_message(call.message.chat.id, "No counselors are available for reassignment.")
