class ServerConfig(object):
    SERVER_HOST = "127.0.0.1"
    SERVER_PORT = 8080
    # в теле запроса от SS о новом заказе
    FULL_TESTING_CODE = "FULL"
    UNIT_TESTING_CODE = "UNIT"
    SERVER_ERROR_MESSAGE = "Ошибка века в сервере"


class ServerMessages(object):
    SUCCEED_FUTURE_RESULT_CODE = 200
    PENDING_FUTURE_RESULT = "выполняется"
    CANCELLED_FUTURE_MESSAGE = "команда была отменена"

    UUID_COMMAND_NOT_FOUND = "команда с таким uuid не найдена"

    ORDER_CREATED_MESSAGE = "заказ успешно принят"
    DOUBLE_ORDER_MESSAGE = "Этот заказ уже находится в обработке"
    NOT_WORKING_HOURS = "Заказы не принимаем, приходите завтра"

    STATE_IS_ON_ALREADY = "Этот режим уже включен"


class KioskModeNames(object):
    STANDBYMODE = "Stand by"
    BEFORECOOKING = "Подготовка к рабочему режиму"
    COOKINGMODE = "Рабочий режим"
    TESTINGMODE = "Режим тестирования"


class CookingModeConst(object):
    OVEN_LIQUIDATION_TIME = 60
    OVEN_FREE_WAITING_TIME = 35
    HALF_STAFF_CHECK_TIME = 60