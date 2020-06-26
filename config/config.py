SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8080

STANDBYMODE = "stand_by"
COOKINGMODE = "cooking_mode"
TESTINGMODE = "testing_mode"
BEFORECOOKING = "before_cooking"

SCHEDULE = {

}

#время в мин до ликвидации заказа после информирования о готовности
OVEN_LIQUIDATION_TIME = 60

OVEN_FREE_WAITING_TIME = 35

QT_DISH_PER_ORDER = 2

HALF_STAFF_CHECK_TIME = 60

with open("config/bot_token.txt") as bot_token:
    DISCORD_TOKEN = bot_token.read().strip()