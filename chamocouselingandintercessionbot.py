import json
from typing import Final
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters

TOKEN: Final = '..'
BOT_USERNAME: Final = '..'
DATA_FILE: Final = 'counselors.json'
client_sessions = {}
counselors = {}
super_admin_id = ..

def load_counselors():
    global counselors
    try:
        with open(DATA_FILE, 'r') as file:
            counselors = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        counselors = {}

def save_counselors():
    with open(DATA_FILE, 'w') as file:
        json.dump(counselors, file)

# Start Command Handler
async def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    if user.id == super_admin_id:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Welcome Super Admin! You can register counselors using /register_counselor.",
                                       reply_markup=ReplyKeyboardMarkup([['Register Counselor'], ['View Counselors']], one_time_keyboard=True))
    elif user.username in counselors:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Hello Counselor, you are now active!")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Welcome to the counseling bot! Please choose an option:",
                                       reply_markup=ReplyKeyboardMarkup([['Start One-on-One Counseling'], ['Join Group Counseling'], ['Change Counselor']], one_time_keyboard=True))

# General message handler
async def handle_message(update: Update, context: CallbackContext):
    user = update.message.from_user
    if user.username not in counselors:
        option = update.message.text
        if option == "Start One-on-One Counseling":
            await assign_counselor(update, context, one_on_one=True)
        elif option == "Join Group Counseling":
            await choose_group_option(update, context)
        elif option == "Change Counselor":
            await change_counselor(update, context)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid option.")
    else:
        await forward_to_client(update, context)

# Group counseling options
async def choose_group_option(update: Update, context: CallbackContext):
    """Presents the user with options for group counseling."""
    client_id = update.effective_chat.id
    await context.bot.send_message(chat_id=client_id,
                                   text="Choose your group counseling option:",
                                   reply_markup=ReplyKeyboardMarkup([['Private with Counselors'], ['Public Discussion']], one_time_keyboard=True))

# Assign counselor
async def assign_counselor(update: Update, context: CallbackContext, one_on_one=False):
    client_id = update.effective_chat.id
    if counselors:
        counselor_username = list(counselors.keys())[0]  # Assign the first available counselor
        client_sessions[client_id] = {
            'counselor': counselor_username,
            'counselor_chat_id': counselors[counselor_username],
            'session_type': 'one_on_one' if one_on_one else 'group'
        }
        await context.bot.send_message(chat_id=client_id, text=f"You have been connected to counselor @{counselor_username}.")
        await context.bot.send_message(chat_id=counselors[counselor_username], text="You have a new client.")
    else:
        await context.bot.send_message(chat_id=client_id, text="No counselors are available at the moment.")

# Forward counselor's message to client
async def forward_to_client(update: Update, context: CallbackContext):
    counselor_username = update.message.from_user.username
    for client_id, session in client_sessions.items():
        if session['counselor'] == counselor_username:
            await context.bot.send_message(chat_id=client_id, text=update.message.text)

# Change counselor
async def change_counselor(update: Update, context: CallbackContext):
    client_id = update.effective_chat.id
    current_session = client_sessions.get(client_id)
    if current_session:
        await context.bot.send_message(chat_id=current_session['counselor_chat_id'],
                                       text="The client has requested a change of counselor.")
        del client_sessions[client_id]
        await assign_counselor(update, context)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not currently assigned to any counselor.")

# Register a counselor by Super Admin
async def register_counselor(update: Update, context: CallbackContext):
    user = update.message.from_user
    if user.id != super_admin_id:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not authorized to register counselors.")
        return

    await context.bot.send_message(chat_id=update.effective_chat.id, text="Please provide the counselor's user ID.")
    context.user_data['pending_registration'] = True  # Set the state for registration

# Handle the counselor's user ID input
async def handle_counselor_user_id(update: Update, context: CallbackContext):
    user = update.message.from_user
    if user.id != super_admin_id:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not authorized to perform this action.")
        return

    if 'pending_registration' not in context.user_data:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No counselor registration is in progress.")
        return

    try:
        counselor_user_id = int(update.message.text)
        context.user_data['pending_counselor_user_id'] = counselor_user_id
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please enter the username of the counselor.")
    except ValueError:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid user ID. Please provide a valid number.")

# Handle the counselor's username input
async def handle_counselor_username(update: Update, context: CallbackContext):
    user = update.message.from_user
    if user.id != super_admin_id:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not authorized to perform this action.")
        return

    if 'pending_counselor_user_id' not in context.user_data:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please provide the user ID first.")
        return

    counselor_username = update.message.text.strip('@')
    counselor_user_id = context.user_data['pending_counselor_user_id']

    if counselor_username in counselors:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Counselor @{counselor_username} is already registered.")
    else:
        counselors[counselor_username] = counselor_user_id
        save_counselors()  # Save counselors to file
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Counselor @{counselor_username} has been registered with user ID {counselor_user_id}.")
    
    context.user_data.pop('pending_registration', None)
    context.user_data.pop('pending_counselor_user_id', None)

# View counselors
async def view_counselors(update: Update, context: CallbackContext):
    user = update.message.from_user
    if user.id != super_admin_id:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not authorized to view counselors.")
        return

    if counselors:
        counselor_list = "\n".join([f"@{username}" for username in counselors.keys()])
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Registered Counselors:\n{counselor_list}")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No counselors registered yet.")

# Main function
def main():
    load_counselors()  # Load counselors from the file at startup

    application = Application.builder().token(TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("register_counselor", register_counselor))
    application.add_handler(CommandHandler("view_counselors", view_counselors))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_counselor_user_id))  # Handle user ID input
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_counselor_username))  # Handle username input

    application.run_polling()

if __name__ == "__main__":
    main()


# from typing import Final
# from telegram import Update, ReplyKeyboardMarkup
# from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters

# TOKEN: Final = '7870966451:AAF-KujeDLKCR8k1zTN7Kl1NSvhxraaw2iU'
# BOT_USERNAME: Final = '@chamocounselingbot'

# # Dictionary to store client-to-counselor mapping and active counselors
# client_sessions = {}
# counselors = {}  # Store active counselors with chat IDs
# super_admin_username = 'https://t.me/edenZee'  # Replace with actual Super Admin's Telegram username


# async def start(update: Update, context: CallbackContext):
#     user = update.message.from_user
#     if user.username == super_admin_username:
#         await context.bot.send_message(chat_id=update.effective_chat.id,
#                                        text="Welcome Super Admin! You can register counselors using /register_counselor.",
#                                        reply_markup=ReplyKeyboardMarkup([['Register Counselor'], ['View Counselors']], one_time_keyboard=True))
#     elif user.username in counselors:
#         await context.bot.send_message(chat_id=update.effective_chat.id, text="Hello Counselor, you are now active!")
#     else:
#         await context.bot.send_message(chat_id=update.effective_chat.id,
#                                        text="Welcome to the counseling bot! Please choose an option:",
#                                        reply_markup=ReplyKeyboardMarkup([['Start Counseling'], ['Change Counselor']], one_time_keyboard=True))


# async def handle_message(update: Update, context: CallbackContext):
#     user = update.message.from_user
#     if user.username not in counselors:
#         # Handle client messages
#         option = update.message.text
#         if option == "Start Counseling":
#             await assign_counselor(update, context)
#         elif option == "Change Counselor":
#             await change_counselor(update, context)
#         else:
#             await context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid option.")
#     else:
#         # Handle counselor messages, forward them to the respective client
#         await forward_to_client(update, context)


# async def assign_counselor(update: Update, context: CallbackContext):
#     client_id = update.effective_chat.id
#     if counselors:
#         counselor_username = list(counselors.keys())[0]  # Assign the first available counselor
#         client_sessions[client_id] = {
#             'counselor': counselor_username,
#             'counselor_chat_id': counselors[counselor_username]
#         }
#         await context.bot.send_message(chat_id=client_id, text=f"You have been connected to counselor @{counselor_username}.")
#         await context.bot.send_message(chat_id=counselors[counselor_username], text="You have a new client.")
#     else:
#         await context.bot.send_message(chat_id=client_id, text="No counselors are available at the moment.")


# async def forward_to_client(update: Update, context: CallbackContext):
#     counselor_username = update.message.from_user.username
#     for client_id, session in client_sessions.items():
#         if session['counselor'] == counselor_username:
#             await context.bot.send_message(chat_id=client_id, text=update.message.text)


# async def change_counselor(update: Update, context: CallbackContext):
#     client_id = update.effective_chat.id
#     current_session = client_sessions.get(client_id)
#     if current_session:
#         await context.bot.send_message(chat_id=current_session['counselor_chat_id'],
#                                        text="The client has requested a change of counselor.")
#         del client_sessions[client_id]
#         await assign_counselor(update, context)
#     else:
#         await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not currently assigned to any counselor.")


# async def register_counselor(update: Update, context: CallbackContext):
#     """Allows Super Admin to register a new counselor."""
#     user = update.message.from_user
#     if user.username != super_admin_username:
#         await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not authorized to register counselors.")
#         return

#     if len(context.args) != 1:
#         await context.bot.send_message(chat_id=update.effective_chat.id, text="Usage: /register_counselor <username>")
#         return

#     counselor_username = context.args[0]
#     if counselor_username in counselors:
#         await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Counselor @{counselor_username} is already registered.")
#     else:
#         counselors[counselor_username] = update.effective_chat.id  # Store counselor chat ID
#         await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Counselor @{counselor_username} has been registered.")


# async def view_counselors(update: Update, context: CallbackContext):
#     """Allows Super Admin to view all registered counselors."""
#     user = update.message.from_user
#     if user.username != super_admin_username:
#         await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not authorized to view counselors.")
#         return

#     if counselors:
#         counselor_list = "\n".join([f"@{username}" for username in counselors.keys()])
#         await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Registered Counselors:\n{counselor_list}")
#     else:
#         await context.bot.send_message(chat_id=update.effective_chat.id, text="No counselors registered yet.")


# def main():
#     application = Application.builder().token(TOKEN).build()

#     # Handlers
#     application.add_handler(CommandHandler("start", start))
#     application.add_handler(CommandHandler("register_counselor", register_counselor))
#     application.add_handler(CommandHandler("view_counselors", view_counselors))
#     application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

#     # Start polling
#     application.run_polling()


# if __name__ == '__main__':
#     main()
