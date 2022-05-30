# Use this generator for create your own "config.yaml"
# Get API token from @BotFather
# Get ChannelID by "curl https://api.telegram.org/bot<token>/getUpdates" after adding ur bot to channel
# "channel_post":{... "sender_chat":{"id": ChannelID,...}}
# Get Admin ID by parsing message.chat from admin
import yaml

print("Set bot API token")
token = input()
print("Set channel ID")
channel_id = input()
print("Admin chatID")
admins = []
while True:
    data = input()
    if data == "":
        break
    admins.append(data)
    print("Another admin ID (leave blank to skip)")
to_yaml = {'bot_api_token': token,
           'channel_id': channel_id,
           'admins': admins}
with open("config.yaml", 'w') as ConfigFile:
    yaml.dump(to_yaml, ConfigFile)
