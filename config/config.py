SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8080

STANDBYMODE = "stand_by"
COOKINGMODE = "cooking_mode"
TESTINGMODE = "testing_mode"
BEFORECOOKING = "before_cooking"

# в теле запроса от SS
NEW_ORDER_ID_KEY = "check_code"

#время в мин до ликвидации заказа после информирования о готовности
OVEN_LIQUIDATION_TIME = 60

OVEN_FREE_WAITING_TIME = 35

QT_DISH_PER_ORDER = 2

HALF_STAFF_CHECK_TIME = 60

with open("config/bot_token.txt") as bot_token:
    DISCORD_TOKEN = bot_token.read().strip()

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
