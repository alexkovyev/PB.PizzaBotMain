""" Это основной модуль (дописать) """
import asyncio
import uuid

from .equipment import Equipment
from kbs.data.server.server_const import ServerConfig, ServerMessages
from kbs.data.kiosk_modes.kiosk_modes import KioskModeNames
from kbs.cntrls_api.ControllerBus import ControllersEvents, event_generator
from kbs.notifications.discord_sender import DiscordBotAccess
# from kbs.task_manager.kiosk_state.CookingMode import CookingMode
from kbs.task_manager.kiosk_state.CookingMode.mode_main import CookingMode
from kbs.task_manager.kiosk_state.CookingMode.before_cooking import BeforeCooking
from kbs.task_manager.kiosk_state import StandByMode
from kbs.task_manager.kiosk_state import TestingMode


class PizzaBotMain(object):
    """ Это основной класс (дописать)

    """
    def __init__(self):
        self.current_instance = StandByMode.StandBy()
        self.equipment = None
        self.events_monitoring = ControllersEvents()
        self.discord_bot_client = DiscordBotAccess()
        self.messages_for_sending = asyncio.Queue()
        self.is_able_to_cook = True
        self.command_status = {}

    @property
    def current_state(self):
        """ Этот метод определяет текущий режим работы киоска для формирования
        корретного ответа сервера на запросы на Api
        :return: str
        """
        if isinstance(self.current_instance, CookingMode):
            return KioskModeNames.COOKINGMODE
        elif isinstance(self.current_instance, StandByMode.StandBy):
            return KioskModeNames.STANDBYMODE
        elif isinstance(self.current_instance, TestingMode.TestingMode):
            return KioskModeNames.TESTINGMODE
        elif isinstance(self.current_instance, BeforeCooking):
            return KioskModeNames.BEFORECOOKING

    async def is_open_for_new_orders(self):
        """Метод определяет можно ли принимать заказы.
        На текущий момент просто проверят, что включен 'Рабочий режим' """
        return True if self.current_state == KioskModeNames.COOKINGMODE else False

    async def cooking_mode_start(self, future=None, params=None):
        """Это метод непосредственно включает режим готовки
        Перед активацией режима готовки необходимо провести подготовительные процедуры:
        - обновить данные об оборудовании
        - спарсить данные рецептов для готовки.
        Поэтому включение состоит их 2х режимов: BEFORECOOKING и COOKING
        :param future: объект футуры, создаваемый при запуске режиме через АПИ
        """
        print("ЗАПУСКАЕМ режим ГОТОВКИ")
        self.current_instance = BeforeCooking()
        if self.equipment is None:
            print("ОШИБКА ОБОРУДОВАНИЯ")
            self.equipment = await self.add_equipment_data()
        (is_ok, self.equipment), recipe = await BeforeCooking.start_pbm(self.equipment)
        self.current_instance = CookingMode(recipe, self.equipment)
        if future is not None and not future.cancelled():
            future.set_result(str(ServerMessages.SUCCEED_FUTURE_RESULT_CODE))
        await self.current_instance.start()

    async def testing_start(self, future, params):
        """ Это супер метод тестов"""
        self.current_instance = TestingMode.TestingMode()
        testing_type, *_ = params

        if testing_type == ServerConfig.FULL_TESTING_CODE:
            # не сделано, поэтому просто sleep
            print("Запускаем тестирование, долгое")
            await asyncio.sleep(60)

        elif testing_type == ServerConfig.UNIT_TESTING_CODE:
            print("Запускаем тестирование узла")
            # не сделано, поэтому просто sleep
            await asyncio.sleep(20)
            print("Тестирование узла завершено")

        self.current_instance = StandByMode.StandBy()
        if future is not None and not future.cancelled():
            future.set_result(str(ServerMessages.SUCCEED_FUTURE_RESULT_CODE))

    async def unit_activation(self, params):
        """Этот метод активирует узел
        :param params: dict вида {"unit_type": str,
                                  "unit_id": uuid}
        """
        unit_type, unit_id = params
        if unit_type != "ovens":
            print("Меняем данные оборудования")
            getattr(self.equipment, unit_type)[unit_id] = True
        else:
            print("Меняем данные печи")
            try:
                self.equipment.ovens.oven_units[unit_id].status = "free"
            except KeyError:
                print("Печь не найдена")
                return "Печь не опознана"
        return str(ServerMessages.SUCCEED_FUTURE_RESULT_CODE)

    async def is_able_to_cook_checker(self):
        """Этот метод проверяет можно ли готовить, то есть работает ли мин необходмое оборудование, те
        - станция нарезки
        - станция упаковки
        - хотя бы 1 из улов выдачи
        """
        is_cut_station_ok = self.equipment.cut_station.values()
        is_package_station_ok = True if any(self.equipment.package_station.values()) else False
        self.is_able_to_cook = True if (is_cut_station_ok and is_package_station_ok) else False

    # on_start_tasks
    async def create_hardware_broke_listener(self):
        """Этот метод запускает бесконечный таск, который отслеживает наступление событий
         поломки оборудования"""
        event_name = "hardware_status_changed"
        event = self.events_monitoring.get_dispatcher_event(event_name)
        while True:
            event_occurrence = await event
            _, event_params = event_occurrence
            print("Сработало событие, обрабатываем")
            await self.current_instance.broken_equipment_handler(event_params, self.equipment)
            await self.is_able_to_cook_checker()
            print("Можем ли готовить", self.is_able_to_cook)

    async def get_equipment_data(self):
        """Это метод - заглушка, который имитрует подключение к БД и получение данных
        об оборудовании"""
        await asyncio.sleep(2)
        oven_ids = [str(uuid.uuid4()) for i in range(1, 22)]
        equipment_data = {
            "ovens": {i: {"oven_id": i, "status": "free"} for i in oven_ids},
            "cut_station": {"f50ec0b7-f960-400d-91f0-c42a6d44e3d0": True},
            "package_station": {"afeb1c10-83ef-4194-9821-491fcf0aa52b": True},
            "sauce_dispensers": {"16ffcee8-2130-4a2f-b71d-469ee65d42d0": True,
                                 "ab5065e3-93aa-4313-869e-50a959458439": True,
                                 "28cc0239-2e35-4ccd-9fcd-be2155e4fcbe": True,
                                 "1b1af602-b70f-42a3-8b5d-3112dcf82c26": True,
                                 },
            "dough_dispensers": {"ebf29d04-023c-4141-acbe-055a19a79afe": True,
                                 "2e84d0fd-a71f-4988-8eee-d0373c0bc609": True,
                                 "68ec7c16-f57b-43c0-b708-dfaea5c2e1dd": True,
                                 "75355f3c-bf05-405d-98af-f04bcba7d7e4": True,
                                 },
            "pick_up_points": {"1431f373-d036-4e0f-b059-70acd6bd18b9": True,
                               "b7f96101-564f-4203-8109-014c94790978": True,
                               "73b194e1-5926-45be-99ec-25e1021b96f7": True,
                               }
        }
        return equipment_data

    async def add_equipment_data(self):
        """Этот метод запускает сбор данных об оборудовании из БД и создает экземпляр класса Equipment"""
        equipment_data = await self.get_equipment_data()
        self.equipment = Equipment(equipment_data)

    async def send_message(self):
        """Это метод-заглушка для тестирования работоспособности отпавки сообщений в Discord """
        message = {
            "message_code": "out_of_stock",
            "message_data": {'id': '1',
                             'address': 'here',
                             'halfstaff_name': 'пельмени',
                             'N': '1',
                             'min_qt': '3'}
        }
        await self.messages_for_sending.put(message)

    async def is_able_to_cook_monitoring(self):
        """Это фоновая задача, отслеживающая можно ли готовитт"""
        while True:
            if not self.is_able_to_cook:
                print("Готовить не можем, выключаем систему")
                # не сделано
            await asyncio.sleep(3)

    async def message_sending_worker(self):
        """Это фоновая задача - отправитель уведомлений"""

        while True:
            if not self.messages_for_sending.empty():
                message_to_send = await self.messages_for_sending.get()
                await self.discord_bot_client.send_messages(message_to_send)
            await asyncio.sleep(1)


pizza_bot_main = PizzaBotMain()
