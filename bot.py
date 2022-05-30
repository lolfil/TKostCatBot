import os
import random

import telebot
import logging
import yaml
import time
import uuid
import shutil

logging.basicConfig(level=logging.DEBUG)

admin_filesize_limit = 10485760
admin_filecount_limit = 1000
nonadmin_filesize_limit = 5242880
nonadmin_filecount_limit = 5


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
    logging.debug("get_current_time_formatted")
    return time.strftime("%H.%m.%S %d.%m.%y ", time.localtime())


def count_files_in_dir(path):
    logging.debug("count_files_in_dir")
    # folder path
    dir_path = path
    count = 0
    # Iterate directory
    for path in os.listdir(dir_path):
        # check if current path is a file
        if os.path.isfile(os.path.join(dir_path, path)):
            count += 1
    return count


def is_user_admin(user_chat_id):
    logging.debug("is_user_admin")
    if str(user_chat_id) in admins:
        return True
    else:
        return False


def is_file_picture(file_path):
    logging.debug("is_file_picture")
    if ".jpg" in file_path or ".png" in file_path or ".jpeg" in file_path:
        return True
    else:
        return False


def check_user_limits(message):
    logging.debug("check_user_limits")
    return admin_filecount_limit - find_pictures_from_user(message.chat.id) if is_user_admin(message.chat.id) \
        else nonadmin_filecount_limit - find_pictures_from_user(message.chat.id)


def pick_a_unverified_pic_from_top(path):
    logging.debug("pick_a_unverified_pic_from_top")
    return os.listdir(path)[0]


def pick_a_random_pic(path):
    logging.debug("pick_a_random_pic")
    folder = os.listdir(path)
    return random.choice(folder)


def find_pictures_from_user(user_chat_id, path):
    logging.debug("find_pictures_from_user")
    count = 0
    for file in os.listdir(path):
        if str(user_chat_id) in file:
            count += 1
    return count

    pass


def message_logger(message_type, message):
    logging.debug("message_logger")
    logging.debug(message_type + " message. With " + message.chat.first_name + " with id: " + str(message.chat.id))


def photo_saver(admin, message):
    logging.debug("photo_saver")
    try:
        file_info = bot.get_file(message.document.file_id)  # get path to file in tg struct
        if is_file_picture(file_info.file_path):
            if file_info.file_size < (admin_filesize_limit if admin else nonadmin_filesize_limit):  # check file size
                if find_pictures_from_user(message.chat.id, 'unverified/') < \
                        (admin_filecount_limit if admin else nonadmin_filecount_limit):  # check limit for files
                    downloaded_file = bot.download_file(file_info.file_path)
                    # rename file and add .jpg
                    src = 'unverified/' + \
                          get_current_time_formatted() + str(message.chat.id) + " " + str(uuid.uuid4()) + ".jpg"
                    with open(src, 'wb') as new_file:
                        new_file.write(downloaded_file)
                    bot.reply_to(message, "Saved! You can upload {} more pictures."
                                 .format(check_user_limits))
                else:
                    bot.send_message(message.chat.id, "Too much pics. Limit for you is {}"
                                     .format(admin_filecount_limit if admin else nonadmin_filecount_limit))
            else:
                bot.reply_to(message, "Oh no, it's too big, oniichan!!! ({} MB is my limit for you, honest)"
                             .format((admin_filesize_limit/1000000) if admin else (nonadmin_filesize_limit/1000000)))
        else:
            bot.reply_to(message, "Oh no, it's looks like not a picture. I understand only .jpg(.jpeg) and .png files.")
    except Exception as e:
        bot.reply_to(message, str(e))
        logging.log(logging.WARN, "Something happened while downloading picture from user " + str(message.chat.id)
                    + " name: " + message.chat.first_name + " Error code is: " + str(e))


@bot.message_handler(content_types=['text'])
def handle_text(message):
    logging.debug("handle_text")
    if message.text == '/start':
        send_start_message(message)
    elif message.text == '/help':
        send_help_message(message)
    elif message.text == '/rules':
        send_rules_message(message)
    elif message.text == '/examples':
        send_examples_message(message)
    elif message.text == '/moderate':
        send_moderate_message(message)
    elif message.text == '/stats':
        send_stats_message(message)
    elif message.text == '/whoami':
        send_whoami_message(message)
    else:
        send_generic_message(message)


@bot.message_handler(content_types=['document'])
def handle_doc(message):
    logging.debug("handle_doc")
    message_logger("Document", message)
    bot.send_message(message.chat.id, "A document? Hmm, let me check...")
    time.sleep(0.1)
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
    logging.debug("handle_photo")
    message_logger("Photo", message)
    bot.send_message(message.chat.id, "You send me a pic, hope it's not a dick-pic. "
                                      "Please send it to me without compression. "
                                      "\nWith mobile version you can do it by pressing clip and send photo as a file")


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    logging.debug("callback_query")
    if call.data == "1":
        shutil.move("unverified/" + call.message.caption.split("\"")[1], 'verified/')
        bot.delete_message(call.message.chat.id, call.message.id-1)
        bot.delete_message(call.message.chat.id, call.message.id)
        bot.answer_callback_query(call.id, "Nice! Added to list.")
    elif call.data == "2":
        shutil.move("unverified/" + call.message.caption.split("\"")[1], 'deleted/')
        bot.delete_message(call.message.chat.id, call.message.id-1)
        bot.delete_message(call.message.chat.id, call.message.id)
        bot.answer_callback_query(call.id, "Awful. Removed.")


def send_start_message(message):
    message_logger("Start", message)
    user_markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    user_markup.row('/start', '/help', '/stats')
    user_markup.row('/rules', '/whoami', '/examples')

    bot.send_message(message.chat.id, "You can send me some pictures of cats. "
                                      "If that's pictures comply our rules I post it to our cat channel. "
                                      "You can try /help if you want some more information.", reply_markup=user_markup)


def send_help_message(message):
    message_logger("Help", message)
    if is_user_admin(message.chat.id):
        bot.send_message(message.chat.id, "For you available:\n/start - start page\n/help - this page\n"
                         "/stats - your posting statistics\n/rules - how to post properly\n"
                         "/moderate - (A)for moderating pics from users\n/debug - (A)for some admin features")
    else:
        bot.send_message(message.chat.id,
                         "For you available\n/start - start page\n/help - this page\n"
                         "/stats - your posting statistics\n/rules - how to post properly\n")


def send_rules_message(message):
    message_logger("Rules", message)
    bot.send_message(message.chat.id, "Here some our basic rules for pictures."
                                      "\nIf you want your great-cat-picture to pass moderation."
                                      "\n0. Moderators may not like your picture. "
                                      "Nothing wrong with you specifically, it just happened."
                                      "\n1. No violence (including guns) or politics. "
                                      "That's totally prohibited, we love cats."
                                      "\n2. No meme or drawings ,yep, only cool real cats."
                                      "\n3. It's about cats. Not about anyone else. "
                                      "No human (except of VERY funny or cool cats with it)"
                                      "\n4. No personal information. We do not need it here."
                                      "\n Try to see /examples if you want to understand more")


def send_examples_message(message):
    message_logger("Examples", message)
    img1 = open('examples/(1)Bad1,2.jpg', 'rb')
    img2 = open('examples/(2)Bad1.jpg', 'rb')
    img3 = open('examples/(3)Bad,3.jpg', 'rb')
    img4 = open('examples/Good.jpg', 'rb')
    photos = [telebot.types.InputMediaPhoto(img1, caption="Bad due to 1 and 2 rules."),
              telebot.types.InputMediaPhoto(img2, caption="Bad due to rule 1. Yep, we don't like guns here."),
              telebot.types.InputMediaPhoto(img3, caption="Bad due to rule 3. It's not a cat!"),
              telebot.types.InputMediaPhoto(img4, caption="Good. We like stuff like this here.")]
    bot.send_media_group(message.chat.id, photos)


def send_moderate_message(message):
    if is_user_admin(message.chat.id):
        message_logger("Moderator", message)
        count = count_files_in_dir('unverified/')
        if count > 0:
            bot.delete_message(message.chat.id, message.id)
            bot.send_message(message.chat.id, "Seems like we have {} pics to check".format(count))
            pic = pick_a_unverified_pic_from_top('unverified/')
            img_path = 'unverified/' + pic
            img = open(img_path, 'rb')
            options = [telebot.types.InlineKeyboardButton('Yes!', callback_data=1),
                       telebot.types.InlineKeyboardButton('No!', callback_data=2)]
            markup = telebot.types.InlineKeyboardMarkup([options])
            bot.send_photo(message.chat.id, img, caption="File: \"" +
                                                         pic + "\" \nIs this a good picture for our cat-channel?",
                           reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "Seems like we don't have any pics from users")
    else:
        bot.send_message(message.chat.id, "I don't have any secret commands. So please leave me alone")


def send_stats_message(message):
    message_logger("Stats", message)
    good = find_pictures_from_user(message.chat.id, "verified/")
    check = find_pictures_from_user(message.chat.id, "unverified/")
    bot.send_message(message.chat.id, "You have {} verified and {} unverified pictures".format(good, check))


def send_generic_message(message):
    message_logger("Generic", message)
    if is_user_admin(message.chat.id):
        bot.send_message(message.chat.id, "ACCESS GRANTED /clear and /moderator for you")
    else:
        bot.send_message(message.chat.id, "Can only take your picture and do what specified in /help. "
                                          "Nothing more, honey.")


def send_whoami_message(message):
    message_logger("Whoami", message)
    if is_user_admin(message.chat.id):
        bot.send_message(message.chat.id, "Admin. /debug and /moderator for you")
    else:
        bot.send_message(message.chat.id, "User. You can upload {} more pictures.".format(check_user_limits))
    pass


logging.info("Bot started.")
bot.infinity_polling()
