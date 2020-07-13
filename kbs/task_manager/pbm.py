""" Это основной модуль (дописать) """
import asyncio

from kbs.data.server_confg.server_const import (ServerConfig,
                                                ServerMessages,
                                                KioskModeNames)
from kbs.cntrls_api.ControllerBus import ControllersEvents, event_generator
from kbs.notifications.discord_sender import DiscordBotAccess
from kbs.task_manager.kiosk_state.CookingMode import CookingMode
from kbs.task_manager.kiosk_state import StandByMode
from kbs.task_manager.kiosk_state import TestingMode


class PizzaBotMain(object):
    """ Это основной класс (дописать)

    """
    def __init__(self):
        self.current_instance = StandByMode.StandBy
        self.equipment = None
        self.events_monitoring = ControllersEvents()
        self.discord_bot_client = DiscordBotAccess()
        self.messages_for_sending = asyncio.Queue()
        self.is_able_to_cook = True

    @property
    def current_state(self):
        """ Этот метод определяет текущий режим работы киоска для формирования
        корретного ответа сервера на запросы на Api
        :return: str
        """
        if isinstance(self.current_instance, CookingMode.CookingMode):
            return KioskModeNames.COOKINGMODE
        elif isinstance(self.current_instance, StandByMode.StandBy):
            return KioskModeNames.STANDBYMODE
        elif isinstance(self.current_instance, TestingMode.TestingMode):
            return KioskModeNames.TESTINGMODE
        elif isinstance(self.current_instance, CookingMode.BeforeCooking):
            return KioskModeNames.BEFORECOOKING

    async def is_open_for_new_orders(self):
        """Метод определяет можно ли принимать заказы.
        На текущий момент просто проверят, что включен 'Рабочий режим' """
        return True if self.current_state == KioskModeNames.COOKINGMODE else False


pizza_bot_main = PizzaBotMain()
