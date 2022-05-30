import os
import telebot
import logging
import yaml
import time
import uuid

logging.basicConfig(level=logging.DEBUG)

admin_filesize_limit = 10485760
admin_filecount_limit = 1000
nonadmin_filesize_limit = 5242880
nonadmin_filecount_limit = 3


# for proxy
# import telebot.apihelper as apihelper
# apihelper.proxy = {'https':'socks5://127.0.0.1:9050'}

# Load configuration
logging.info("Reading configuration.")

with open("config.yaml") as ConfigFile:
    config = yaml.safe_load(ConfigFile)
    token = config.get("bot_api_token")
    channel_id = config.get("channel_id")
    admins = config.get("admins")
    ConfigFile.close()
    if (token == "") or (channel_id == "") and (admins == ""):
        logging.critical("Some error occurred while reading configuration. Closing app.")
        quit(0)

logging.info("Configuration read successfully.")

# Starting bot with token.
bot = telebot.TeleBot(token)


def get_current_time_formatted():
    return time.strftime("%d.%m.%y %H.%m.%S ", time.localtime())


def count_files_in_dir(path):
    # folder path
    dir_path = path
    count = 0
    # Iterate directory
    for path in os.listdir(dir_path):
        # check if current path is a file
        if os.path.isfile(os.path.join(dir_path, path)):
            count += 1
    return count


def message_logger(message_type, message):
    logging.debug(message_type + " message. With " + message.chat.first_name + " with id: " + str(message.chat.id))


def is_user_admin(user_chat_id):
    if str(user_chat_id) in admins:
        return True
    else:
        return False


def is_file_picture(file_path):
    if ".jpg" in file_path or ".png" in file_path:
        return True
    else:
        return False


@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text == '/start':
        send_start_message(message)
    elif message.text == '/help':
        send_help_message(message)
    elif message.text == '/clear':
        send_clear_message(message)
    elif message.text == '/moderator':
        check_pictures_message(message)
    elif message.text.lower() == 'any message':
        send_secret_message(message)
    else:
        send_generic_message(message)


def photo_saver(admin, message):
    try:
        file_info = bot.get_file(message.document.file_id)  # get path to file in tg struct
        if is_file_picture(file_info.file_path):
            if file_info.file_size < (admin_filesize_limit if admin else nonadmin_filesize_limit):  # check file size
                if not admin and not os.path.exists(str(message.chat.id) + "/"):  # temporary solution for storing pics
                    os.makedirs(str(message.chat.id) + "/")  # create folder if not exist
                if count_files_in_dir(('photos/' if admin else (str(message.chat.id) + '/'))) < \
                        (admin_filecount_limit if admin else nonadmin_filecount_limit):  # check limit for files
                    downloaded_file = bot.download_file(file_info.file_path)
                    src = ('photos/' if admin else (str(message.chat.id) + '/')) + \
                        get_current_time_formatted() + str(uuid.uuid4()) + ".jpg"  # rename file and add .jpg
                    with open(src, 'wb') as new_file:
                        new_file.write(downloaded_file)
                    bot.reply_to(message, "Saved!")
                else:
                    bot.send_message(message.chat.id, "Too much pics. Limit for you is {}"
                                     .format(admin_filecount_limit if admin else nonadmin_filecount_limit))
            else:
                bot.reply_to(message, "Oh no, it's too big, oniichan!!! ({} MB is my limit for you, honestly)"
                             .format((admin_filesize_limit/1000000) if admin else (nonadmin_filesize_limit/1000000)))
        else:
            bot.reply_to(message, "Oh no, it's looks like not a picture. I understand only .jpg and .png files.")
    except Exception as e:
        bot.reply_to(message, str(e))
        logging.log(logging.WARN, "Something happened while downloading picture from user " + str(message.chat.id)
                    + " name: " + message.chat.first_name + " Error code is: " + str(e))


@bot.message_handler(content_types=['document'])
def handle_doc(message):

    message_logger("Document", message)
    bot.send_message(message.chat.id, "A document? Hmm, let me check...")
    # For admin(aka whitelisted user) we have no limit for pictures and save it directly to main folder
    if is_user_admin(message.chat.id):
        photo_saver(True, message)
    # For non-admin(aka non-whitelisted user) we have limited for pictures and save it to user folder (for moderating)
    else:
        bot.send_message(message.chat.id, "Seems like u not in my whitelist... "
                                          "I'm not interested in your silly pictures! But this one...")
        photo_saver(False, message)


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    message_logger("Photo", message)
    bot.send_message(message.chat.id, "You send me a pic, hope it's not a dick-pic. "
                                      "Please send it to me without compression. "
                                      "\nWith mobile version you can do it by pressing clip and send photo as file")


def check_pictures_message(message):
    pass


def send_start_message(message):
    message_logger("Start", message)
    bot.send_message(message.chat.id, "Hi. I'm bot created for posting some cat pics in one channel. Just for fun.")


def send_help_message(message):
    message_logger("Help", message)
    bot.send_message(message.chat.id, "There is nothing helpful for u. "
                     + "I support only /start and /help messages for my guests.")


def send_generic_message(message):
    message_logger("Generic", message)
    if is_user_admin(message.chat.id):
        bot.send_message(message.chat.id, "ACCESS GRANTED")
    else:
        bot.send_message(message.chat.id, "I don't have any secret commands. So please leave me alone")


def send_clear_message(message):
    message_logger("Clear", message)
    if is_user_admin(message.chat.id):
        bot.send_message(message.chat.id, "It's experimental feature, honeybon. "
                                          "I can try it, but only with messages by last 48 hour. "
                                          "And i don't know why you need this, but it might not working. "
                                          "You have 5 seconds to say bye")
        time.sleep(5)
        for i in reversed(range(1, message.id+2)):
            print(i)
            bot.delete_message(message.chat.id, i)
    else:
        bot.send_message(message.chat.id, "It's experimental feature, honeybon, only for admins.")


def send_secret_message(message):
    message_logger("Secret", message)
    logging.info(message.from_user.first_name)
    bot.send_message(message.chat.id, "You are funny and found my secret message, "
                     + "write to my creator, maybe he will treat you to a beer (no)")


logging.info("Bot started.")
bot.infinity_polling()
