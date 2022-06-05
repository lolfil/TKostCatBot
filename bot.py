import os
import random
import telebot
import logging
import yaml
import time
import uuid
import shutil
import io

from PIL import Image
from apscheduler.schedulers.background import BackgroundScheduler

# TODO tests, docker.

config_path = 'config.yaml'
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-8s %(name)-25s  %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S', )


def count_files_in_dir(path):
    logging.debug("count_files_in_dir: " + str(path))
    # folder path
    dir_path = path
    count = 0
    # Iterate directory
    for path in os.listdir(dir_path):
        # check if current path is a file
        if os.path.isfile(os.path.join(dir_path, path)):
            count += 1
    return count


def find_pictures_from_user(user_chat_id, path):
    logging.debug("find_pictures_from_user " + str(user_chat_id) + str(path))
    count = 0
    for file in os.listdir(path):
        if str(user_chat_id) in file:
            count += 1
    return count


def get_current_time_formatted():
    logging.debug("get_current_time_formatted")
    return time.strftime("%d-%m-%y_%H-%m-%S", time.localtime())


def is_file_picture(file_path):
    logging.debug("is_file_picture " + str(file_path))
    if ".jpg" in file_path or ".png" in file_path or ".jpeg" in file_path:
        return True
    else:
        return False


def message_logger(message_type, message):
    logging.debug(
        message_type + " message. With " + str(message.chat.first_name) + " with id: " + str(message.chat.id))


def pick_a_random_pic(path):
    logging.debug("pick_a_random_pic " + str(path))
    folder = os.listdir(path)
    return random.choice(folder)


def pick_a_unverified_pic_from_top(path):
    logging.debug("pick_a_unverified_pic_from_top " + str(path))
    return os.listdir(path)[0]


class MyBot:
    def __init__(self, config):
        self.scheduler = BackgroundScheduler()
        self.admin_file_size_limit = None
        self.admin_file_count_limit = None
        self.non_admin_file_size_limit = None
        self.non_admin_file_count_limit = None
        self.path_to_deleted = None
        self.path_to_examples = None
        self.path_to_posted = None
        self.path_to_unverified = None
        self.path_to_verified = None
        self.token = None
        self.channel_id = None
        self.admins = None

        self.read_config(config)  # Read config from file
        self.bot = telebot.TeleBot(self.token)
        # Posts image in channel every day on 8:35
        self.scheduler.add_job(self.post_image_in_channel, 'cron', hour=8)

        @self.bot.message_handler(content_types=['text'])
        def handle_text(message):
            logging.debug("handle_text")
            if message.text == '/start':
                self.send_start_message(message)
            elif message.text == '/help':
                self.send_help_message(message)
            elif message.text == '/rules':
                self.send_rules_message(message)
            elif message.text == '/examples':
                self.send_examples_message(message)
            elif message.text == '/stats':
                self.send_stats_message(message)
            elif message.text == '/whoami':
                self.send_whoami_message(message)
            elif message.text == '/moderate':  # Admins
                self.send_moderate_message(message)
            elif message.text == '/test':  # Admins
                self.send_test_message(message)
            else:
                self.send_generic_message(message)

        @self.bot.message_handler(content_types=['document'])
        def handle_doc(message):
            logging.debug("handle_doc")
            message_logger("Document", message)
            self.bot.send_message(message.chat.id, "A document? Hm-m, let me check...")
            time.sleep(0.1)  # is it necessary?
            if self.is_user_admin(message.chat.id):
                self.photo_saver(True, message)
            else:
                self.bot.send_message(message.chat.id, "Seems like u not in my list of good-people... "
                                                       "I'm not interested in your silly pictures! But this one...")
                self.photo_saver(False, message)

        @self.bot.message_handler(content_types=['photo'])
        def handle_photo(message):
            logging.debug("handle_photo")
            message_logger("Photo", message)
            self.bot.send_message(message.chat.id, "You send me a pic, hope it's good-cat pic. "
                                                   "Please send it to me without compression.\n"
                                                   "From mobile you can do it by pressing clip and send pic as a file")

        @self.bot.message_handler(content_types=['sticker'])
        def handle_sticker(message):
            logging.debug("handle_sticker")
            message_logger("Sticker", message)
            print(message)
            self.bot.send_message(message.chat.id, "You send me a sticker?\n"
                                                   "Sometimes when you send a .webp image from windows desktop client "
                                                   "telegram think it's a sticker\n"
                                                   "Telegram team sad \"This behaviour is intended.\"\n"
                                                   "Maybe we do something with that in future, but now you can convert "
                                                   "it on https://image.online-convert.com/ru/convert/webp-to-jpg")

        @self.bot.callback_query_handler(func=lambda call: True)
        def callback_query(call):
            #  We use callbacks for moderating functions. Two buttons appear with moderating photo.
            logging.debug("callback_query")
            if call.data == "1":
                shutil.move(self.path_to_unverified + call.message.caption.split("\"")[1], self.path_to_verified)
                self.bot.delete_message(call.message.chat.id, call.message.id - 1)
                self.bot.delete_message(call.message.chat.id, call.message.id)
                self.bot.answer_callback_query(call.id, "Nice! Added to list.")
            elif call.data == "2":
                shutil.move(self.path_to_unverified + call.message.caption.split("\"")[1], self.path_to_deleted)
                self.bot.delete_message(call.message.chat.id, call.message.id - 1)
                self.bot.delete_message(call.message.chat.id, call.message.id)
                self.bot.answer_callback_query(call.id, "Awful. Removed.")

        self.scheduler.start()  # Start scheduler here.
        self.bot.polling(True)

    def check_user_limits(self, message):
        logging.debug("check_user_limits " + str(message.chat.id))
        return self.admin_file_count_limit - find_pictures_from_user(message.chat.id, self.path_to_unverified) \
            if self.is_user_admin(message.chat.id) \
            else (self.non_admin_file_count_limit
                  - find_pictures_from_user(message.chat.id, self.path_to_unverified))

    def is_user_admin(self, user_chat_id):
        logging.debug("is_user_admin " + str(user_chat_id))
        if str(user_chat_id) in self.admins:
            return True
        else:
            return False

    def photo_saver(self, admin, message):
        logging.debug("photo_saver")
        try:
            file_info = self.bot.get_file(message.document.file_id)  # get path to file in tg struct
            if is_file_picture(file_info.file_path):
                if file_info.file_size < (self.admin_file_size_limit
                   if admin
                   else self.non_admin_file_size_limit):  # check file size
                    if find_pictures_from_user(message.chat.id, self.path_to_unverified) < \
                            (self.admin_file_count_limit
                             if admin
                             else self.non_admin_file_count_limit):  # check limit for files
                        downloaded_file = self.bot.download_file(file_info.file_path)
                        im = Image.open(io.BytesIO(downloaded_file)).convert("RGB")  # read as byte-array
                        # build a path for file: unverified/ + time + userID + uni-string + .jpg
                        src = self.path_to_unverified \
                            + get_current_time_formatted() \
                            + " " \
                            + str(message.chat.id) \
                            + " " \
                            + str(uuid.uuid4()) \
                            + ".jpg"
                        im.save(src, "jpeg")  # save as jpeg
                        self.bot.reply_to(message, "Saved! You can upload {} more pictures."
                                          .format(self.check_user_limits(message)))
                    else:
                        self.bot.send_message(message.chat.id, "Too much pics. Limit for you is {}"
                                              .format(self.admin_file_count_limit
                                                      if admin
                                                      else self.non_admin_file_count_limit))
                else:
                    self.bot.reply_to(message, "Oh no, it's too big, step-bro!!! ({} MB is my limit for you, honest)"
                                      .format((self.admin_file_size_limit / 1000000)
                                              if admin
                                              else (self.non_admin_file_size_limit / 1000000)))
            else:
                self.bot.reply_to(message,
                                  "Oh no, it's looks like not a picture. I understand only .jpg(.jpeg) and .png files.")
        except Exception as e:
            self.bot.reply_to(message, str(e))
            logging.warning("Something happened while downloading picture from user "
                            + str(message.chat.id)
                            + " name: "
                            + message.chat.first_name
                            + " Error code is: "
                            + str(e))

    def post_image_in_channel(self):
        logging.debug("post_image_in_channel")
        try:
            img_path = self.path_to_verified + pick_a_random_pic(self.path_to_verified)
            img = open(img_path, 'rb')
            self.bot.send_photo(self.channel_id, img, caption=img_path)
            img.close()
            shutil.move(img_path, self.path_to_posted)
        except Exception as e:
            logging.warning("Something bad occurred during posting pictures." + str(e))

        how_much_pics_we_have = count_files_in_dir(self.path_to_verified)
        if how_much_pics_we_have < 10:
            self.bot.send_message(self.admins[0], "Running out of cats, we have only {}".format(how_much_pics_we_have))

    def read_config(self, cfg_path):
        logging.info("Reading configuration.")
        with open(cfg_path) as ConfigFile:
            config = yaml.safe_load(ConfigFile)
            self.token = config.get("bot_api_token")
            self.channel_id = config.get("channel_id")
            self.admins = config.get("admins")
            self.admin_file_size_limit = config.get("admin_file_size_limit")
            self.admin_file_count_limit = config.get("admin_file_count_limit")
            self.non_admin_file_size_limit = config.get("non_admin_file_size_limit")
            self.non_admin_file_count_limit = config.get("non_admin_file_count_limit")
            self.path_to_deleted = config.get("path_to_deleted")
            self.path_to_examples = config.get("path_to_examples")
            self.path_to_posted = config.get("path_to_posted")
            self.path_to_unverified = config.get("path_to_unverified")
            self.path_to_verified = config.get("path_to_verified")
            ConfigFile.close()
            if (self.token == "") or (self.channel_id == "") and (self.admins == ""):
                logging.critical("Some error occurred while reading important configurations. Closing app.")
                quit(0)
        logging.info("Configuration successfully loaded.")

    # All message handlers below

    def send_start_message(self, message):
        message_logger("Start", message)
        user_markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        user_markup.row('/start', '/help', '/stats')
        user_markup.row('/rules', '/whoami', '/examples')
        if self.is_user_admin(message.chat.id):
            user_markup.row('/moderate', '/placeholder', '/test')

        self.bot.send_message(message.chat.id, "You can send me some pictures of cats. "
                                               "If that's pictures comply our rules I post it to our cat channel. "
                                               "You can try /help if you want some more information.",
                              reply_markup=user_markup)

    def send_help_message(self, message):
        message_logger("Help", message)
        message_text = "For you available" \
                       "\n/start - start page" \
                       "\n/help - this page" \
                       "\n/stats - your posting statistics" \
                       "\n/rules - how to post properly " \
                       "\n/whoami - check your status and upload limit"
        if self.is_user_admin(message.chat.id):
            message_text += "\n/moderate - (A)for moderating pics from users" \
                            "\n/test - (A)test posting, test message, test all types of logs, press with caution"
        self.bot.send_message(message.chat.id, message_text)

    def send_rules_message(self, message):
        message_logger("Rules", message)
        self.bot.send_message(message.chat.id, "Here some our basic rules for pictures."
                                               "\nIf you want your great-cat-picture to pass moderation."
                                               "\n0. Moderators may not like your picture. "
                                               "Nothing wrong with you, it just happened."
                                               "\n1. No violence (including guns) or politics. "
                                               "That's totally prohibited, we love cats."
                                               "\n2. No memes or drawings, yep, only cool real cats."
                                               "\n3. It's about cats. Not about anyone else. "
                                               "No humans (except of VERY funny or cool cats with it)"
                                               "\n4. No personal information. We do not need it here."
                                               "\nTry to see /examples if you want to understand more")

    def send_examples_message(self, message):
        message_logger("Examples", message)
        img1 = open(self.path_to_examples + '(1)Bad1,2.jpg', 'rb')
        img2 = open(self.path_to_examples + '(2)Bad1.jpg', 'rb')
        img3 = open(self.path_to_examples + '(3)Bad,3.jpg', 'rb')
        img4 = open(self.path_to_examples + '(4)Bad,2.jpg', 'rb')
        img5 = open(self.path_to_examples + 'Good.jpg', 'rb')

        photos = [telebot.types.InputMediaPhoto(img1, caption="Bad due to rules #1 and #2."),
                  telebot.types.InputMediaPhoto(img2, caption="Bad due to rule #1. Yep, we don't like guns here."),
                  telebot.types.InputMediaPhoto(img3, caption="Bad due to rule #3. It's not a cat!"),
                  telebot.types.InputMediaPhoto(img4, caption="Bad due to rule #2, memes prohibited"),
                  telebot.types.InputMediaPhoto(img5, caption="Good. We like stuff like this here.")]
        self.bot.send_media_group(message.chat.id, photos)

    def send_stats_message(self, message):
        message_logger("Stats", message)
        good = find_pictures_from_user(message.chat.id, self.path_to_verified)
        check = find_pictures_from_user(message.chat.id, self.path_to_unverified)
        posted = find_pictures_from_user(message.chat.id, self.path_to_posted)
        deleted = find_pictures_from_user(message.chat.id, self.path_to_deleted)
        message_text = "Cats we have from you:" \
                       "\n{} verified ({} of it already posted)." \
                       "\n{} unverified pictures." \
                       "\n{} deleted".format(good + posted, posted, check, deleted)
        if self.is_user_admin(message.chat.id):
            message_text += ("\n\nCats we have from all people:"
                             "\n{} verified and ready for posting."
                             "\n{} unverified."
                             "\n{} already posted now."
                             "\n{} deleted."
                             .format(count_files_in_dir(self.path_to_verified),
                                     count_files_in_dir(self.path_to_unverified),
                                     count_files_in_dir(self.path_to_posted),
                                     count_files_in_dir(self.path_to_deleted)))
        self.bot.send_message(message.chat.id, message_text)

    def send_whoami_message(self, message):
        message_logger("Whoami", message)
        if self.is_user_admin(message.chat.id):
            self.bot.send_message(message.chat.id, "Admin./moderate and /test for you")
        else:
            self.bot.send_message(message.chat.id,
                                  "User. You can upload {} more pictures.".format(self.check_user_limits(message)))
        pass

    def send_moderate_message(self, message):
        if self.is_user_admin(message.chat.id):
            message_logger("Moderator", message)
            count = count_files_in_dir(self.path_to_unverified)
            if count > 0:
                self.bot.delete_message(message.chat.id, message.id)
                self.bot.send_message(message.chat.id, "Seems like we have {} pics to check".format(count))
                pic = pick_a_unverified_pic_from_top(self.path_to_unverified)
                img_path = self.path_to_unverified + pic
                img = open(img_path, 'rb')
                options = [telebot.types.InlineKeyboardButton('Yes!', callback_data=1),
                           telebot.types.InlineKeyboardButton('No!', callback_data=2)]
                markup = telebot.types.InlineKeyboardMarkup([options])
                self.bot.send_photo(message.chat.id, img,
                                    caption="File: \""
                                            + pic
                                            + "\" \nIs this a good picture for our cat-channel?",
                                    reply_markup=markup)
            else:
                self.bot.send_message(message.chat.id, "Seems like we don't have any pics from users")
        else:
            self.bot.send_message(message.chat.id, "I don't have any secret commands. So please leave me alone")

    def send_test_message(self, message):
        logging.debug("send_test_message")
        logging.debug("Did u see me? I am a test logging message on DEBUG level.")
        logging.info("Did u see me? I am a test logging message on INFO level.")
        logging.warning("Did u see me? I am a test logging message on WARNING level.")
        logging.error("Did u see me? I am a test logging message on ERROR level.")
        logging.critical("Did u see me? I am a test logging message on CRITICAL level.")

        if self.is_user_admin(message.chat.id):
            self.post_image_in_channel()
        else:
            self.send_generic_message(message)
        self.bot.send_message(self.admins[0], 'Someone used /test command')

    def send_generic_message(self, message):
        message_logger("Generic", message)
        self.bot.send_message(message.chat.id,
                              "Can only take your picture and do what specified in /help. Nothing more, honey.")


logging.info("Starts bot...")
MyBot(config_path)
