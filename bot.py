import os
import random
import telebot
import logging
import yaml
import time
import uuid
import shutil

from apscheduler.schedulers.background import BackgroundScheduler
config_path = 'config.yaml'
logging.basicConfig(level=logging.DEBUG)
# TODO tests, docker.


class MyBot:
    # TODO move as maximum settings as possible to generator
    admin_file_ize_limit = 10485760
    admin_file_count_limit = 1000
    non_admin_file_size_limit = 5242880
    non_admin_filecount_limit = 15

    path_to_deleted = 'pics/deleted/'
    path_to_examples = 'pics/examples/'
    path_to_posted = 'pics/posted/'
    path_to_unverified = 'pics/unverified/'
    path_to_verified = 'pics/verified/'

    token = ''
    channel_id = ''
    admins = ''
    scheduler = BackgroundScheduler()

    def __init__(self, config):
        self.read_config(config)  # Read config from file
        self.bot = telebot.TeleBot(self.token)
        # Posts image in channel every day on 23:00
        self.scheduler.add_job(self.post_image_in_channel, 'cron', hour=23)

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
                self.test_post_pic(message)
            else:
                self.send_generic_message(message)

        @self.bot.message_handler(content_types=['document'])
        def handle_doc(message):
            logging.debug("handle_doc")
            self.message_logger("Document", message)
            self.bot.send_message(message.chat.id, "A document? Hmm, let me check...")
            time.sleep(0.1)
            if self.is_user_admin(message.chat.id):
                self.photo_saver(True, message)
            else:
                self.bot.send_message(message.chat.id, "Seems like u not in my whitelist... "
                                                       "I'm not interested in your silly pictures! But this one...")
                self.photo_saver(False, message)

        @self.bot.message_handler(content_types=['photo'])
        def handle_photo(message):
            logging.debug("handle_photo")
            self.message_logger("Photo", message)
            self.bot.send_message(message.chat.id, "You send me a pic, hope it's not a dick-pic. "
                                                   "Please send it to me without compression.\n"
                                                   "From mobile you can do it by pressing clip and send pic as a file")

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
        self.bot.polling()

    def read_config(self, cfg_path):
        logging.info("Reading configuration.")
        with open(cfg_path) as ConfigFile:
            config = yaml.safe_load(ConfigFile)
            self.token = config.get("bot_api_token")
            self.channel_id = config.get("channel_id")
            self.admins = config.get("admins")
            ConfigFile.close()
            if (self.token == "") or (self.channel_id == "") and (self.admins == ""):
                logging.critical("Some error occurred while reading configuration. Closing app.")
                quit(0)
        logging.info("Configuration read successfully.")

    def send_message(self):
        self.bot.send_message(self.admins[0], 'Test message with 30 sec interval')

    @staticmethod
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

    @staticmethod
    def get_current_time_formatted():
        logging.debug("get_current_time_formatted")
        return time.strftime("%H.%m.%S %d.%m.%y ", time.localtime())

    def is_user_admin(self, user_chat_id):
        logging.debug("is_user_admin " + str(user_chat_id))
        if str(user_chat_id) in self.admins:
            return True
        else:
            return False

    @staticmethod
    def is_file_picture(file_path):
        logging.debug("is_file_picture " + str(file_path))
        if ".jpg" in file_path or ".png" in file_path or ".jpeg" in file_path:
            return True
        else:
            return False

    def check_user_limits(self, message):
        logging.debug("check_user_limits " + str(message.chat.id))
        return self.admin_file_count_limit - self.find_pictures_from_user(message.chat.id, self.path_to_unverified) \
            if self.is_user_admin(message.chat.id) \
            else self.non_admin_filecount_limit - self.find_pictures_from_user(message.chat.id, self.path_to_unverified)

    @staticmethod
    def pick_a_unverified_pic_from_top(path):
        logging.debug("pick_a_unverified_pic_from_top " + str(path))
        return os.listdir(path)[0]

    @staticmethod
    def pick_a_random_pic(path):
        logging.debug("pick_a_random_pic " + str(path))
        folder = os.listdir(path)
        return random.choice(folder)

    @staticmethod
    def find_pictures_from_user(user_chat_id, path):
        logging.debug("find_pictures_from_user " + str(user_chat_id) + str(path))
        count = 0
        for file in os.listdir(path):
            if str(user_chat_id) in file:
                count += 1
        return count

        pass

    @staticmethod
    def message_logger(message_type, message):
        logging.debug("message_logger")
        logging.debug(
            message_type + " message. With " + str(message.chat.first_name) + " with id: " + str(message.chat.id))

    def photo_saver(self, admin, message):
        logging.debug("photo_saver")
        try:
            file_info = self.bot.get_file(message.document.file_id)  # get path to file in tg struct
            if self.is_file_picture(file_info.file_path):
                if file_info.file_size < (self.admin_file_ize_limit
                                          if admin
                                          else self.non_admin_file_size_limit):  # check file size
                    if self.find_pictures_from_user(message.chat.id, self.path_to_unverified) < \
                            (self.admin_file_count_limit
                             if admin
                             else self.non_admin_filecount_limit):  # check limit for files
                        downloaded_file = self.bot.download_file(file_info.file_path)
                        # rename file and add .jpg
                        src = self.path_to_unverified \
                            + self.get_current_time_formatted() \
                            + str(message.chat.id) \
                            + " " \
                            + str(uuid.uuid4()) + ".jpg"
                        with open(src, 'wb') as new_file:
                            new_file.write(downloaded_file)
                        self.bot.reply_to(message, "Saved! You can upload {} more pictures."
                                          .format(self.check_user_limits(message)))
                    else:
                        self.bot.send_message(message.chat.id, "Too much pics. Limit for you is {}"
                                              .format(self.admin_file_count_limit
                                                      if admin
                                                      else self.non_admin_filecount_limit))
                else:
                    self.bot.reply_to(message, "Oh no, it's too big, step-bro!!! ({} MB is my limit for you, honest)"
                                      .format((self.admin_file_ize_limit / 1000000)
                                              if admin
                                              else (self.non_admin_file_size_limit / 1000000)))
            else:
                self.bot.reply_to(message,
                                  "Oh no, it's looks like not a picture. I understand only .jpg(.jpeg) and .png files.")
        except Exception as e:
            self.bot.reply_to(message, str(e))
            logging.log(logging.WARN, "Something happened while downloading picture from user " + str(message.chat.id)
                        + " name: " + message.chat.first_name + " Error code is: " + str(e))

    def send_start_message(self, message):
        self.message_logger("Start", message)
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
        self.message_logger("Help", message)
        message_text = "For you available\n/start - start page\n/help - this page" \
                       "\n/stats - your posting statistics\n/rules - how to post properly " \
                       "\n/whoami - check your status and upload limit"
        if self.is_user_admin(message.chat.id):
            message_text += "\n/moderate - (A)for moderating pics from users\n/debug - (A)for some admin features"
        self.bot.send_message(message.chat.id, message_text)

    def send_rules_message(self, message):
        self.message_logger("Rules", message)
        self.bot.send_message(message.chat.id, "Here some our basic rules for pictures."
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

    def send_examples_message(self, message):
        self.message_logger("Examples", message)
        img1 = open(self.path_to_examples + '(1)Bad1,2.jpg', 'rb')
        img2 = open(self.path_to_examples + '(2)Bad1.jpg', 'rb')
        img3 = open(self.path_to_examples + '(3)Bad,3.jpg', 'rb')
        img4 = open(self.path_to_examples + 'Good.jpg', 'rb')
        photos = [telebot.types.InputMediaPhoto(img1, caption="Bad due to 1 and 2 rules."),
                  telebot.types.InputMediaPhoto(img2, caption="Bad due to rule 1. Yep, we don't like guns here."),
                  telebot.types.InputMediaPhoto(img3, caption="Bad due to rule 3. It's not a cat!"),
                  telebot.types.InputMediaPhoto(img4, caption="Good. We like stuff like this here.")]
        self.bot.send_media_group(message.chat.id, photos)

    def send_moderate_message(self, message):
        if self.is_user_admin(message.chat.id):
            self.message_logger("Moderator", message)
            count = self.count_files_in_dir(self.path_to_unverified)
            if count > 0:
                self.bot.delete_message(message.chat.id, message.id)
                self.bot.send_message(message.chat.id, "Seems like we have {} pics to check".format(count))
                pic = self.pick_a_unverified_pic_from_top(self.path_to_unverified)
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

    def send_stats_message(self, message):
        self.message_logger("Stats", message)
        good = self.find_pictures_from_user(message.chat.id, self.path_to_verified)
        check = self.find_pictures_from_user(message.chat.id, self.path_to_unverified)
        posted = self.find_pictures_from_user(message.chat.id, self.path_to_posted)
        message_text = "You have {} verified ({} of it already posted)" \
                       " and {} unverified pictures".format(good + posted, posted, check)
        if self.is_user_admin(message.chat.id):
            message_text += ("\nAlso {} pics ready for posting and {} for verifying. {} already posted now"
                             .format(self.count_files_in_dir(self.path_to_verified),
                                     self.count_files_in_dir(self.path_to_unverified),
                                     self.count_files_in_dir(self.path_to_posted)))
        self.bot.send_message(message.chat.id, message_text)

    def send_generic_message(self, message):
        self.message_logger("Generic", message)
        self.bot.send_message(message.chat.id,
                              "Can only take your picture and do what specified in /help. Nothing more, honey.")

    def send_whoami_message(self, message):
        self.message_logger("Whoami", message)
        if self.is_user_admin(message.chat.id):
            self.bot.send_message(message.chat.id, "Admin. /debug and /moderate for you")
        else:
            self.bot.send_message(message.chat.id,
                                  "User. You can upload {} more pictures.".format(self.check_user_limits(message)))
        pass

    def test_post_pic(self, message):
        if self.is_user_admin(message.chat.id):
            self.post_image_in_channel()
        else:
            self.send_generic_message(message)

    def post_image_in_channel(self):
        logging.debug("post_image_in_channel")
        try:
            img_path = self.path_to_verified + self.pick_a_random_pic(self.path_to_verified)
            img = open(img_path, 'rb')
            self.bot.send_photo(self.admins[0], img, caption=img_path)
            img.close()
            shutil.move(img_path, self.path_to_posted)
        except Exception as e:
            logging.warning("Something bad occurred during posting pictures." + str(e))

        how_much_pics_we_have = self.count_files_in_dir(self.path_to_verified)
        if how_much_pics_we_have < 10:
            self.bot.send_message(self.admins[0], "Running out of cats, we have only {}".format(how_much_pics_we_have))


logging.info("Starts bot...")
MyBot(config_path)
