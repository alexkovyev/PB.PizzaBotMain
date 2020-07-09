class DiscordConfg(object):
    DISCORD_ADMIN_CHANNEL_NAME = "admin"
    DISCORD_OPERATOR_CHANNEL_NAME = "operator"
    DISCORD_TEMPLATES = {
        'end_of_shelf_life': {
            'text': "На объекте PIzzaBot {id} по адресу {address} осталось {N} порций продукта "
                    "{halfstaff_name} при мин остатке {min_qt}.",
            'receivers': ('operator', 'admin')
        },
        'out_of_stock': {
            'text': "На объекте PIzzaBot {id} по адресу {address} осталось {N} порций продукта {"
                    "halfstaff_name} при мин остатке {min_qt}.",
            'receivers': ('operator', 'admin')
        }
    }
    with open("data/discord_confg/bot_token.txt") as bot_token:
        DISCORD_TOKEN = bot_token.read().strip()