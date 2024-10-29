from telethon import TelegramClient, events, functions
from telethon.tl.types import InputPeerChannel
from telebot import TeleBot
import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# File to store counselor data
COUNSELOR_FILE = 'counselors.json'
SESSION_LOG_DIR = 'sessions'
api_id = 'YOUR_API_ID'  # Replace with your actual API ID
api_hash = 'YOUR_API_HASH'  # Replace with your actual API Hash
# Set up the Telethon client and bot
client = TelegramClient('session_name', api_id, api_hash, timeout=10)
bot = telebot.TeleBot(API_TOKEN)
logging.basicConfig(level=logging.INFO)

# Fetch messages from a chat
async def fetch_topics(chat_id):
    try:
        async with app:
            # Retrieve all topics in the group
            dialogs = await app.get_dialogs()
            for dialog in dialogs:
                if dialog.chat.id == chat_id and dialog.is_topic:
                    topic_id = dialog.id  # The unique ID for each topic
                    print(f"Topic found: {dialog.title}, ID: {topic_id}")

                    # Fetch messages for each topic
                    async for message in app.get_chat_history(chat_id, topic_id=topic_id, limit=20):
                        print(message.text)
    except errors.PeerIdInvalid:
        print(f"Invalid peer ID for chat_id: {chat_id}")
    except Exception as e:
        print(f"An error occurred: {e}")

async def get_chat_id(group_username):
    async with app:
        chat = await app.get_chat(group_username)
        print(f"Chat ID for '{group_username}' is: {chat.id}")

# Replace 'group_username' with the group's @username or invite link
your_chat_id = asyncio.run(get_chat_id('group_username'))


# Run the main function with asyncio
topics = asyncio.run(fetch_topics(your_chat_id))
print(topics)


user_data = {}
reply_data = {}

# Ensure counselors file and sessions directory exist
if not os.path.exists(COUNSELOR_FILE):
    with open(COUNSELOR_FILE, 'w') as f:
        json.dump([], f)
if not os.path.exists(SESSION_LOG_DIR):
    os.makedirs(SESSION_LOG_DIR)


# Helper function to load counselors
def load_counselors():
    try:
        with open(COUNSELOR_FILE, 'r') as f:
            counselors = json.load(f)
            # Ensure counselors is a list
            if not isinstance(counselors, list):
                logging.error("Counselor data is not in list format, resetting to an empty list.")
                return []
            logging.info(f"Loaded counselors: {counselors}")  # Log the loaded counselors
            return counselors  # Ensure this returns a list
    except json.JSONDecodeError:
        logging.error("Failed to decode JSON, resetting counselor data.")
        return []  # Return an empty list if JSON is invalid
    except Exception as e:
        logging.error(f"Failed to load counselors: {e}")
        return []  # Return an empty list on failure


# Helper function to save counselors
def save_counselors(counselors):
    with open(COUNSELOR_FILE, 'w') as f:
        json.dump(counselors, f, indent=4)

def send_welcome(message):
    # Determine the role of the user
    if message.from_user.id in admins:
        welcome_text = "Welcome, Admin! You have full access to manage the bot."
    elif message.from_user.id in counselors:
        welcome_text = "Welcome, Counselor! You can assist users with their queries."
    else:
        welcome_text = (
            "Welcome to the Chamo Counseling Bot.\n\n"
            "This is a safe space to share your struggles, secrets, testimonies, and more anonymously "
            "to a community of supportive individuals.\n\n"
            "Click on start to begin sharing..."
        )
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Start", callback_data="start"))
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)
        
# Register a new counselor (admin only)
@bot.message_handler(commands=['register_counselor'])
def register_counselor(message):
    if message.from_user.id not in admins:
        bot.reply_to(message, "You are not authorized to perform this action.")
        return

    msg = bot.reply_to(message, "Enter the counselor's username:")
    bot.register_next_step_handler(msg, save_counselor)

def save_counselor(message):
    username = message.text.strip()
    counselors = load_counselors()

    # Check if the username already exists
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
    username = message.text.strip()  # Get username from the message
    counselors = load_counselors()

    # Check if the username exists in the list
    if any(c['username'] == username for c in counselors):
        # Filter out the counselor
        counselors = [c for c in counselors if c['username'] != username]  
        save_counselors(counselors)
        bot.reply_to(message, f"Counselor @{username} has been removed.")
    else:
        bot.reply_to(message, f"Counselor @{username} not found.")

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
    session_file = os.path.join(SESSION_LOG_DIR, f"{session_id}.txt")
    with open(session_file, 'w') as f:
        f.write(f"Session started between {user_id} and counselor @{counselor_username}\n")

    bot.send_message(user_id, "You are now in a session with your counselor. Please start sharing.")
    user_data[user_id] = {'counselor': counselor_username, 'session_file': session_file}

# Log user messages to session file
@bot.message_handler(func=lambda message: message.from_user.id in user_data)
def log_session_message(message):
    user_id = message.from_user.id
    session_info = user_data[user_id]
    session_file = session_info['session_file']

    with open(session_file, 'a') as f:
        f.write(f"{datetime.now()} - {message.text}\n")

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
        user_data[user_id]['counselor'] = available_counselor['username']
        bot.send_message(user_id, f"You've been reassigned to counselor @{available_counselor['username']}.")
        bot.send_message(call.message.chat.id, f"{anonymous_name} has been reassigned to counselor @{available_counselor['username']}.")
    else:
        bot.send_message(call.message.chat.id, "No counselors are available for reassignment.")


def receive_message(message):
    user_data[message.chat.id] = {'message': message}
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [InlineKeyboardButton(topic, callback_data=topic) for topic in topics.keys()]

    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i + 2])
    markup.add(InlineKeyboardButton("Go Back", callback_data="go_back"))

    topic_msg = bot.send_message(message.chat.id, "Please choose a topic for your message.", reply_markup=markup)
    user_data[message.chat.id]['topic_msg_id'] = topic_msg.message_id

@bot.callback_query_handler(func=lambda call: call.data in topics.keys() or call.data == "go_back")
def preview_message(call):
    if call.data == "go_back":
        ask_for_message(call)
        return

    bot.delete_message(call.message.chat.id, call.message.message_id)  # Delete the topic selection message
    user_data[call.message.chat.id]['topic'] = call.data
    chosen_topic = call.data
    msg = user_data[call.message.chat.id]['message']

    caption = f"#{chosen_topic.replace(' ', '_')}\n" + (msg.caption if msg.caption else "")

    # Preview the message with the correct content type
    if msg.content_type == "text":
        preview_text = caption + msg.text
        preview_msg = bot.send_message(call.message.chat.id, f"Preview:\n\n{preview_text}")
    elif msg.content_type == "photo":
        preview_msg = bot.send_photo(call.message.chat.id, msg.photo[-1].file_id, caption=caption)
    elif msg.content_type == "video":
        preview_msg = bot.send_video(call.message.chat.id, msg.video.file_id, caption=caption)
    elif msg.content_type == "voice":
        preview_msg = bot.send_voice(call.message.chat.id, msg.voice.file_id, caption=caption)
    elif msg.content_type == "audio":
        preview_msg = bot.send_audio(call.message.chat.id, msg.audio.file_id, caption=caption)
    else:
        bot.send_message(call.message.chat.id, "Unsupported message type./start")
        return

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Edit", callback_data="edit"))
    markup.add(InlineKeyboardButton("Send", callback_data="send"))
    markup.add(InlineKeyboardButton("Go Back", callback_data="go_back"))
    choice_msg = bot.send_message(call.message.chat.id, "Would you like to edit, send, or go back?", reply_markup=markup)

    user_data[call.message.chat.id]['preview_msg_id'] = preview_msg.message_id
    user_data[call.message.chat.id]['choice_msg_id'] = choice_msg.message_id

@bot.callback_query_handler(func=lambda call: call.data == "edit")
def edit_message(call):
    bot.delete_message(call.message.chat.id, user_data[call.message.chat.id]['preview_msg_id'])  # Delete the preview message
    bot.delete_message(call.message.chat.id, user_data[call.message.chat.id]['choice_msg_id'])  # Delete the edit/send choice message
    msg = bot.send_message(call.message.chat.id, "Please send the edited message. (text, photo, video, or voice).")
    bot.register_next_step_handler(msg, receive_message)

@bot.callback_query_handler(func=lambda call: call.data == "send")
def send_to_admin(call):
    bot.delete_message(call.message.chat.id, user_data[call.message.chat.id]['preview_msg_id'])  # Delete the preview message
    bot.delete_message(call.message.chat.id, user_data[call.message.chat.id]['choice_msg_id'])  # Delete the edit/send choice message
    user_message = user_data[call.message.chat.id]['message']
    topic = user_data[call.message.chat.id]['topic']
    caption = f"#{topic.replace(' ', '_')}\n\n" + (user_message.caption if user_message.caption else "")

    for admin_id in admins:
        if user_message.content_type == "text":
            bot.send_message(admin_id, f"New message for approval:\n\n{caption + user_message.text}")
        elif user_message.content_type == "photo":
            bot.send_photo(admin_id, user_message.photo[-1].file_id, caption=caption)
        elif user_message.content_type == "video":
            bot.send_video(admin_id, user_message.video.file_id, caption=caption)
        elif user_message.content_type == "voice":
            bot.send_voice(admin_id, user_message.voice.file_id, caption=caption)
        elif user_message.content_type == "audio":
            bot.send_audio(admin_id, user_message.audio.file_id, caption=caption)

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Approve", callback_data=f"approve_{call.message.chat.id}"))
        markup.add(InlineKeyboardButton("Decline", callback_data=f"decline_{call.message.chat.id}"))
        bot.send_message(admin_id, "Approve or Decline?", reply_markup=markup)

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Go Back", callback_data="go_back"))
    bot.send_message(
    call.message.chat.id,
    "Your message has been sent for approval.\n\nOnce your story is posted to the community (@OntoTheLight) we'll send you a notification here so that you can read and listen to feedbacks from the community.\n\nThank you for your patience and for sharing with us. ",
    reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_"))
def approve_message(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    user_id = int(call.data.split("_")[1])
    user_message = user_data[user_id]['message']
    topic = user_data[user_id]['topic']
    message_thread_id = topics[topic]
    group_msg = None  # Initialize group_msg to ensure it's in scope

    try:
        if user_message.content_type == "text":
            group_msg = bot.send_message(
                GROUP_CHAT_ID,
                f"{user_message.text}",
                message_thread_id=message_thread_id
            )
        elif user_message.content_type == "photo":
            group_msg = bot.send_photo(
                GROUP_CHAT_ID,
                user_message.photo[-1].file_id,
                caption=(user_message.caption if user_message.caption else ""),
                message_thread_id=message_thread_id
            )
        elif user_message.content_type == "video":
            group_msg = bot.send_video(
                GROUP_CHAT_ID,
                user_message.video.file_id,
                caption= (user_message.caption if user_message.caption else ""),
                message_thread_id=message_thread_id
            )
        elif user_message.content_type == "voice":
            group_msg = bot.send_voice(
                GROUP_CHAT_ID,
                user_message.voice.file_id,
                caption= (user_message.caption if user_message.caption else ""),
                message_thread_id=message_thread_id
            )
        elif user_message.content_type == "audio":
            group_msg = bot.send_audio(
                GROUP_CHAT_ID,
                user_message.audio.file_id,
                caption= (user_message.caption if user_message.caption else ""),
                message_thread_id=message_thread_id
            )
        for admin_id in admins:
            if admin_id != call.from_user.id:
                bot.send_message(admin_id, "The message has been posted to the group by another admin.")


    except Exception as e:
        bot.send_message(call.message.chat.id, f"Failed to send message: {e}")

    if group_msg:
        reply_markup = InlineKeyboardMarkup()
        reply_markup.add(InlineKeyboardButton(
            "Answer Anonymously",
            url=f"https://t.me/ontothelightbot?start=reply_{group_msg.message_id}"
        ))


    bot.edit_message_reply_markup(GROUP_CHAT_ID, group_msg.message_id, reply_markup=reply_markup)
    message_link = f"https://t.me/c/2248181172/{group_msg.message_id}"
    # Send the confirmation message with the link to the user
    #bot.send_message(user_id, f"Your Message Has Been Approved and Posted.\n\n{message_link}")
    bot.send_message(
        user_id,f"Tour message has been approved. \n\nSee Message: <a href='https://t.me/c/2248181172/{group_msg.message_id}'>click here</a>",
        parse_mode='HTML')


# Help messages for different roles
def get_help_message(user_id):
    if user_id in admins:
        return (
            "Admin Help:\n"
            "- Manage users and sessions.\n"
            "- Add or remove counselors.\n"
            "- View active sessions.\n"
            "- Use /view_counselors to see registered counselors.\n"
            "- Use /end_session to end a user's session."
        )
    elif user_id in counselors:
        return (
            "Counselor Help:\n"
            "- Assist users with their issues.\n"
            "- Respond to anonymous messages.\n"
            "- Use /view_sessions to see your active sessions."
        )
    else:
        return (
            "User Help:\n"
            "- Send messages anonymously to share your experiences.\n"
            "- Click 'Start' to begin sharing.\n"
            "- Your identity remains confidential."
        )

# Handle start command with reply deep link
@bot.message_handler(commands=['start'])
def handle_start(message):
    if len(message.text.split()) > 1 and message.text.split()[1].startswith('reply_'):
        handle_deep_link_reply(message)
    else:
        send_welcome(message)  # Call the new send_welcome function

# Help command handler
@bot.message_handler(commands=['help'])
def handle_help(message):
    help_message = get_help_message(message.from_user.id)
    bot.send_message(message.chat.id, help_message)
def handle_deep_link_reply(message):
    try:
        # Extract the message ID from the deep link
        sent_message_id = int(message.text.split("_")[-1])

        # Copy the touched message to the user's chat to show them what they are replying to
        bot.copy_message(message.chat.id, GROUP_CHAT_ID, sent_message_id)

        bot.send_message(
            message.chat.id,
            "This is the message you are replying to anonymously. Please send your reply."
        )

        # Register the next step to handle the user's reply
        bot.register_next_step_handler(message, get_reply_content, sent_message_id)

    except Exception as e:
        bot.send_message(message.chat.id, f"Could not retrieve the message: {e}")

def get_reply_content(message, sent_message_id):
    if message.text and message.text.startswith("/start reply_"):
        bot.send_message(message.chat.id, "Please send a /start to send a message.")
        return

    try:
        # Handle the user's reply and forward it to the group chat
        send_reply(message, sent_message_id)

    except Exception as e:
        bot.send_message(message.chat.id, f"Failed to process the reply: {e}")

def send_reply(message, touched_message_id):
    try:
        # Send the reply to the touched message in the group chat
        if message.content_type == "text":
            sent_message = bot.send_message(GROUP_CHAT_ID, message.text, reply_to_message_id=touched_message_id)
        elif message.content_type == "photo":
            sent_message = bot.send_photo(GROUP_CHAT_ID, message.photo[-1].file_id, caption=message.caption, reply_to_message_id=touched_message_id)
        elif message.content_type == "video":
            sent_message = bot.send_video(GROUP_CHAT_ID, message.video.file_id, caption=message.caption, reply_to_message_id=touched_message_id)
        elif message.content_type == "voice":
            sent_message = bot.send_voice(GROUP_CHAT_ID, message.voice.file_id, caption=message.caption, reply_to_message_id=touched_message_id)
        elif message.content_type == "audio":
            sent_message = bot.send_audio(GROUP_CHAT_ID, message.audio.file_id, caption=message.caption, reply_to_message_id=touched_message_id)
        else:
            bot.send_message(message.chat.id, "Unsupported message type. Please try again.")
            return

        # Create an inline keyboard for "Reply Anonymously" button using sent_message_id
        markup = InlineKeyboardMarkup()
        reply_url = f"https://t.me/{bot.get_me().username}?start=reply_{sent_message.message_id}"
        markup.add(InlineKeyboardButton("Reply Anonymously", url=reply_url))

        # Edit the sent message to include the reply button
        bot.edit_message_reply_markup(GROUP_CHAT_ID, sent_message.message_id, reply_markup=markup)

        # Notify the user that their reply was sent
        bot.send_message(
            message.chat.id,
            f'Your reply has been posted anonymously. <a href="https://t.me/c/2248181172/{sent_message.message_id}">See here</a>',
            parse_mode='HTML'
        )

    except Exception as e:
        bot.send_message(message.chat.id, f"Failed to send reply: {e}")



@bot.callback_query_handler(func=lambda call: call.data.startswith("decline_"))
def decline_message(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    user_id = int(call.data.split("_")[1])
    bot.send_message(user_id, "Your Message Has Been Declined.")


# Function to dynamically add admins
def add_admin(admin_id):
    if admin_id not in admins:
        admins.append(admin_id)
        return f"Admin with ID {admin_id} added."
    return "Admin Already Exists."


# Function to dynamically add topics
def add_topic(name):
    if name in topics:
        return f"Topic '{name}' already exists."
    topics[name] = True  # Use a simple dictionary to track existence
    return f"Topic '{name}' added."

# Command handlers for adding admins and topics dynamically
@bot.message_handler(commands=['add_admin'])
def handle_add_admin(message):
    if message.from_user.id in admins:  # Ensure only existing admins can add new ones
        try:
            new_admin_id = int(message.text.split()[1])
            response = add_admin(new_admin_id)
        except (IndexError, ValueError):
            response = "Usage: /add_admin <admin_id>"
    else:
        response = "You Are Not an Admin!!!."
    bot.reply_to(message, response)

@bot.message_handler(commands=['add_topic'])
async def handle_add_topic(message):
    if message.from_user.id in admins:  # Ensure only existing admins can add topics
        try:
            args = message.text.split()
            topic_name = args[1]
            topic_icon = '💡'  # Example icon (light bulb)

            # Create the topic in the group
            result = await client(functions.channels.CreateForumTopicRequest(
                channel=GROUP_CHAT_ID,
                title=topic_name,
                icon=topic_icon  # Set the chosen icon here
            ))
            
            # Store the topic name and ID
            topics[topic_name] = result.id
            
            response = f"Topic '{topic_name}' created successfully!"
        except IndexError:
            response = "Usage: /add_topic <topic_name>"
        except Exception as e:
            response = f"Failed to create topic: {str(e)}"
    else:
        response = "You are not an admin!"

    bot.reply_to(message, response)

# Command to view all topics
@bot.message_handler(commands=['view_topics'])
async def view_topics(message):
    if message.from_user.id not in admins:
        bot.reply_to(message, "You are not authorized to perform this action.")
        return

    if not topics:
        bot.reply_to(message, "No topics have been added.")
    else:
        # Fetch group entity
        group = await client.get_entity(GROUP_CHAT_ID)

        # Get the group description (topic)
        description = group.about if group.about else "No description available."
        
        # Create a list of topics
        topic_list = "\n".join(topics.keys())
        
        response = f"Group Description: {description}\n\nTopics:\n{topic_list}"
        bot.reply_to(message, response)

# View all registered counselors
@bot.message_handler(commands=['view_counselors'])
def view_counselors(message):
    if message.from_user.id not in admins:
        bot.reply_to(message, "You are not authorized to perform this action.")
        return
    
    counselors = load_counselors()
    if not counselors:
        bot.reply_to(message, "No counselors registered.")
    else:
        counselor_list = "\n".join([f"@{c['username']} - {'Assigned' if c['assigned'] else 'Available'}" for c in counselors])
        bot.send_message(message.chat.id, f"Registered Counselors:\n{counselor_list}")

# View all active sessions
@bot.message_handler(commands=['view_sessions'])
def view_sessions(message):
    if message.from_user.id not in admins:
        bot.reply_to(message, "You are not authorized to perform this action.")
        return
    
    active_sessions = [f"{user_data[user_id]['counselor']} - User_{user_id}" for user_id in user_data]
    if not active_sessions:
        bot.reply_to(message, "No active sessions.")
    else:
        session_list = "\n".join(active_sessions)
        bot.send_message(message.chat.id, f"Active Sessions:\n{session_list}")

# End a session
@bot.message_handler(commands=['end_session'])
def end_session(message):
    if message.from_user.id not in admins:
        bot.reply_to(message, "You are not authorized to perform this action.")
        return
    
    msg = bot.reply_to(message, "Enter the username of the counselor whose session you want to end:")
    bot.register_next_step_handler(msg, confirm_end_session)

def confirm_end_session(message):
    counselor_username = message.text
    # Find users with this counselor
    users_to_end = [user_id for user_id, data in user_data.items() if data['counselor'] == counselor_username]
    
    if not users_to_end:
        bot.reply_to(message, f"No active sessions with counselor @{counselor_username}.")
        return
    
    # End the session for each user
    for user_id in users_to_end:
        user_data.pop(user_id)  # Remove from active sessions
        bot.send_message(user_id, f"Your session with counselor @{counselor_username} has been ended.")
    
    bot.reply_to(message, f"Ended sessions for @{counselor_username}.")

# Start polling
bot.polling()
