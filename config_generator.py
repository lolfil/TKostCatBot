# Use this generator for create your own "config.yaml"
# Get API token from @BotFather
# Get ChannelID by "curl https://api.telegram.org/bot<token>/getUpdates" after adding ur bot to channel
# "channel_post":{... "sender_chat":{"id": ChannelID,...}}
# Get Admin ID by parsing message.chat from admin
import yaml


def settings_reader_with_default_value(name, default_value):
    print("Set " + name + " (leave blank to use default = {}".format(default_value)+")")
    while True:
        input_data = input()
        if input_data == "":
            return default_value
        else:
            return input_data


def settings_reader_without_default_value(name):
    print("Set " + name)
    while True:
        input_data = input()
        if input_data == "":
            print("Cannot be blank")
        else:
            return input_data


def settings_reader_with_multiple_options(name):
    print("Set " + name)
    options = []
    while True:
        data = input()
        if data == "":
            break
        options.append(data)
        print("Another admin ID (leave blank to skip)")
    return options


def start_generator():
    print("It's a config generator for bot. Follow the instructions, and we set all settings for bot.")
    token = settings_reader_without_default_value("bot API token")
    channel_id = settings_reader_without_default_value("channel ID")
    admins = settings_reader_with_multiple_options("Admin chatID")

    admin_file_size_limit = settings_reader_with_default_value("admin_file_size_limit", 10485760)
    non_admin_file_size_limit = settings_reader_with_default_value("non_admin_file_size_limit", 5242880)
    admin_file_count_limit = settings_reader_with_default_value("admin_file_count_limit", 1000)
    non_admin_file_count_limit = settings_reader_with_default_value("non_admin_file_count_limit", 15)

    path_to_deleted = settings_reader_with_default_value('path_to_deleted', 'pics/deleted/')
    path_to_examples = settings_reader_with_default_value('path_to_examples', 'pics/examples/')
    path_to_posted = settings_reader_with_default_value('path_to_posted', 'pics/posted/')
    path_to_unverified = settings_reader_with_default_value('path_to_unverified', 'pics/unverified/')
    path_to_verified = settings_reader_with_default_value('path_to_verified', 'pics/verified/')

    to_yaml = {'bot_api_token': token,
               'channel_id': channel_id,
               'admins': admins,
               'admin_file_size_limit': admin_file_size_limit,
               'non_admin_file_size_limit': non_admin_file_size_limit,
               'admin_file_count_limit': admin_file_count_limit,
               'non_admin_file_count_limit': non_admin_file_count_limit,
               'path_to_deleted': path_to_deleted,
               'path_to_examples': path_to_examples,
               'path_to_posted': path_to_posted,
               'path_to_unverified': path_to_unverified,
               'path_to_verified': path_to_verified}
    with open("config.yaml", 'w') as ConfigFile:
        yaml.dump(to_yaml, ConfigFile)
    ConfigFile.close()