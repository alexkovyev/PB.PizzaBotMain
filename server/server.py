""" Этот модуль описывает http сервер и фоновые задачи, запускаемые на старте
НЕ реализовано:
- аутентификация
"""
import asyncio
from aiohttp import web
import time
import uuid

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config.config import (SERVER_HOST, SERVER_PORT,
                           STANDBYMODE, BEFORECOOKING, COOKINGMODE, TESTINGMODE,
                           NEW_ORDER_ID_KEY, SUCCEED_FUTURA_RESULT,
                           FULL_TESTING_CODE, UNIT_TESTING_CODE)
from controllers.ControllerBus import ControllersEvents, event_generator
from kiosk_state.CookingMode import CookingMode
from kiosk_state import StandByMode, TestingMode
from notifications.discord_sender import DiscordBotAccess
from server.equipment import Equipment


class PizzaBotMain(object):
    """ Это основной класс приложения, запускаемый при старте системы

    self.current_state - это текущий режим работы киоска

    self.equipment - это экземпляр класса Equipment, при создании None

    self.events_monitoring - это экземпляр класса генератора событий шины контроллеров

    self.command_status - это словарь-хранилище футур, созданных для отправленных на API команд
                          для отслеживания результата выполнения

    self.is_able_to_cook - это флаг - индикатор того, что минимальное необходимое оборудование работает

    self.current_instance - это экземпляр класса текущего режима работы киоска

    self.messages_for_sending - это очередь, в которую попадают все сообщения
                                от разных компонентов системы

    """

    def __init__(self):
        self.current_instance = StandByMode.StandBy()
        self.equipment = None
        self.events_monitoring = ControllersEvents()
        self.command_status = {}
        self.discord_bot_client = DiscordBotAccess()
        self.messages_for_sending = asyncio.Queue()
        self.is_able_to_cook = True

    @property
    def current_state(self):
        stand_by_mode = STANDBYMODE
        cooking_mode = COOKINGMODE
        testing_mode = TESTINGMODE
        before_cooking = BEFORECOOKING

        if isinstance(self.current_instance, CookingMode.CookingMode):
            return cooking_mode
        elif isinstance(self.current_instance, StandByMode.StandBy):
            return stand_by_mode
        elif isinstance(self.current_instance, TestingMode.TestingMode):
            return testing_mode
        elif isinstance(self.current_instance, CookingMode.BeforeCooking):
            return before_cooking

    def create_server(self):
        """Этот метод создает приложение aiohttp сервера, а также привязывает routes api
        для связи с внешними компонентами (админ панель и экран приема заказов)
        :return: aiohttp server app instance
        """
        app = web.Application()
        self.setup_routes(app)
        return app

    def create_scheduler(self):
        """Этот метод создает планровщик для запуска команд по расписанию"""
        scheduler = AsyncIOScheduler()
        scheduler.add_job(self.turn_on_cooking_mode, 'cron', day_of_week='*', hour='10', minute=0, second=0)
        scheduler.add_job(self.turn_off_cooking_mode, 'cron', day_of_week='*', hour='21', minute=0, second=0)
        return scheduler

    def setup_routes(self, app):
        """ Этот метод связывает доступные эндпоинты и обработчики
        :param app: aiohttp server app instance
        """
        app.add_routes([
            web.get("/api/current_state", self.kiosk_current_state_handler),
            web.post("/api/new_order", self.new_order_handler),
            web.post("/api/commands/cooking_mode", self.turn_cooking_mode_handler),
            web.get("/api/commands/status", self.status_command),
            # web.post("/api/commands/stopping_cooking_mode", self.turn_off_cooking_mode_handler),
            web.post("/api/commands/full_system_testing", self.start_full_testing_handler),
            web.post("/api/commands/unit_testing", self.start_unit_testing_handler),
            web.post("/api/commands/unit_activation", self.unit_activation_handler),
        ])

    # API handlers
    async def new_order_handler(self, request):
        """Этот метод обрабатывает запросы приема новых заказов в зависимости от текущего режима киоска,
        запускает создание нового заказа при необходимости.
        """
        if not request.body_exists:
            raise web.HTTPNoContent
        request_body = await request.json()
        new_order_id = request_body[NEW_ORDER_ID_KEY]
        can_receive_new_order = await self.is_open_for_new_orders()
        if can_receive_new_order:
            try:
                is_it_new_order = await self.current_instance.checking_order_for_double(new_order_id)
                if is_it_new_order:
                    await asyncio.create_task(self.current_instance.create_new_order(new_order_id))
                    message = "Заказ успешно принят"
                    raise web.HTTPCreated(text=message)
                else:
                    message = "Этот заказ уже находится в обработке"
                    raise web.HTTPOk(text=message)
            except AttributeError:
                print("Не создан инстанс cooking mode или метод не найден")
                raise web.HTTPServerError(text="Ошибка века в сервере")
        else:
            message = "Заказы не принимаем, приходите завтра"
            raise web.HTTPNotAcceptable(text=message)

    async def kiosk_current_state_handler(self, request):
        """Этот метод обрабатывает запрос на Апи о получении данных о текущем статусе киоска
        Может быть:
        - Stand_by
        - Testing
        - Before_cooking
        - Cooking
        """
        print("Получили запрос текущего статуса киоска")
        current_state = self.current_state
        return web.Response(text=current_state)

    async def status_command(self, request):
        """Этот метод обрабатывает запрос о том, выполнена ли команда, отправленная на АПИ"""

        print("Запрос на статус команды")
        if not request.body_exists:
            raise web.HTTPNoContent
        request_body = await request.json()
        command_uuid = request_body["command_uuid"]
        try:
            result = await self.get_futura_result(self.command_status[command_uuid])
            if result == SUCCEED_FUTURA_RESULT:
                self.command_status.pop(command_uuid)
            return web.Response(text=result)
        except KeyError:
            raise web.HTTPBadRequest(text="uuid не найден")

    async def turn_cooking_mode_handler(self, request):
        """Этот метод обрабатывает запроса на включение режима готовки """
        print("Получили запрос на включение режима готовки")
        if self.current_state == COOKINGMODE or self.current_state == BEFORECOOKING:
            await self.responce_state_is_already_on()

        elif self.current_state == STANDBYMODE:
            response = await self.turn_any_mode(self.cooking_mode_start)
            return web.Response(text=response)

        elif self.current_state == TESTINGMODE:
            await self.responce_state_is_busy(TESTINGMODE)

    async def turn_off_cooking_mode_handler(self, request):
        """Этот метод обрабатывает запрос на выключение режима готовки
        НЕ сделано :(         """
        print("Получили запрос на выключение режима готовки")
        # не сделано :(
        pass

    async def start_full_testing_handler(self, request):
        """Этот метод обрабатывает запрос на запуск полного тестирования системы"""
        print("Получили запрос на включение режима готовки")
        if self.current_state == COOKINGMODE:
            await self.responce_state_is_busy()

        elif self.current_state == STANDBYMODE:
            params = {"testing_type": FULL_TESTING_CODE}
            response = await self.turn_any_mode(self.testing_start, params)
            return web.Response(text=response)

        elif self.current_state == TESTINGMODE:
            await self.responce_state_is_already_on()

    async def start_unit_testing_handler(self, request):
        """Этот метод обрабатывает запрос на тестирование отдельного узла"""
        if self.current_state == STANDBYMODE:
            if not request.body_exists:
                raise web.HTTPNoContent
            request_body = await request.json()
            params = {"testing_type": UNIT_TESTING_CODE,
                      "unit_type": request_body["unit_type"],
                      "unit_id": request_body["unit_id"]}
            response = await self.turn_any_mode(self.testing_start, params)
            return web.Response(text=response)
        else:
            await self.responce_state_is_busy(self.current_state)

    async def unit_activation_handler(self, request):
        """Этот метод обрабатывает активацию отдельного узла"""
        if not request.body_exists:
            raise web.HTTPNoContent
        request_body = await request.json()
        params = {"unit_type": request_body["unit_type"],
                  "unit_id": request_body["unit_id"]}
        message = await self.unit_activation(params)
        return web.Response(text=message)

    # Schedule handlers
    async def turn_on_testing_mode(self, mode):
        """Этот метод обрабатывает запуск режима тестирования по расписанию
        НЕ сделано :( """
        pass

    async def turn_on_cooking_mode(self):
        """Этот метод обрабатывает запуск режима готовки по расписанию"""
        IMPOSSIBLE_TO_TURN_ON_STATES = [TESTINGMODE, COOKINGMODE, BEFORECOOKING]
        if self.current_state == STANDBYMODE:
            await self.cooking_mode_start()
        elif self.current_state in IMPOSSIBLE_TO_TURN_ON_STATES:
            print("киоск занят, не могу включить")
        print("Режим готовки активирован", self.current_state)

    async def turn_off_cooking_mode(self):
        """Этот метод обрабатывает выключение режима готовки по расписанию
         НЕ сделано :( """
        pass

    # utils for handlers
    async def cooking_mode_start(self, future=None):
        """Это метод непосредственно включает режим готовки
        Перед активацией режима готовки необходимо провести подготовительные процедуры:
        - обновить данные об оборудовании
        - спарсить данные рецептов для готовки.
        Поэтому включение состоит их 2х режимов: BEFORECOOKING и COOKING
        :param future: объект футуры, создаваемый при запуске режиме через АПИ
        """
        print("ЗАПУСКАЕМ режим ГОТОВКИ")
        # self.current_state = BEFORECOOKING
        self.current_instance = CookingMode.BeforeCooking()
        if self.equipment is None:
            print("ОШИБКА ОБОРУДОВАНИЯ")
            self.equipment = await self.add_equipment_data()
        (is_ok, self.equipment), recipe = await CookingMode.BeforeCooking.start_pbm(self.equipment)
        self.current_instance = CookingMode.CookingMode(recipe, self.equipment)
        if future is not None and not future.cancelled():
            future.set_result(SUCCEED_FUTURA_RESULT)
        await self.current_instance.run()

    async def testing_start(self, future, *args):
        """ Это супер метод тестов"""
        self.current_instance = TestingMode.TestingMode()

        if args[0]["testing_type"] == FULL_TESTING_CODE:
            # не сделано, поэтому просто sleep
            print("Запускаем тестирование, долгое")
            await asyncio.sleep(60)

        elif args[0]["testing_type"] == UNIT_TESTING_CODE:
            print("Запускаем тестирование узла")
            # не сделано, поэтому просто sleep
            await asyncio.sleep(20)
            print("Тестирование узла завершено")

        # self.current_state = STANDBYMODE
        self.current_instance = StandByMode.StandBy()
        if future is not None and not future.cancelled():
            future.set_result(SUCCEED_FUTURA_RESULT)

    async def is_open_for_new_orders(self):
        """Метод определяет можно ли принимать заказы"""
        return True if self.current_state == COOKINGMODE else False

    async def get_futura_result(self, futura):
        """Этот метод проверяет, выполнена ли команда и формирует результат"""
        if futura.done():
            try:
                my_result = futura.result()
            except asyncio.CancelledError:
                my_result = "command was cancelled"
        else:
            my_result = "proceeding"
        return my_result

    async def create_result_future(self):
        """Этот метод создает футуру на каждый запрос выполнения команды, отпарвленный на API
        добавляет в словарь всех футур """
        operation_result = asyncio.get_running_loop().create_future()
        operation_result_uuid = str(uuid.uuid4())
        self.command_status[operation_result_uuid] = operation_result
        return operation_result_uuid, operation_result

    async def turn_any_mode(self, task_name, *args):
        """Этот метод включает заданный режим киоска по запросу, отправленному на API
        :param task_name: небходимый метод
        """
        print("Ок, включаем")
        operation_result_uuid, operation_result = await self.create_result_future()
        asyncio.create_task(task_name(operation_result, *args))
        response = f"uuid:{operation_result_uuid}"
        return response

    async def responce_state_is_already_on(self):
        """Это шаблон ответа, что запрашиваемый режим уже включен"""
        print("Этот режим уже включен")
        raise web.HTTPNotAcceptable(text="Этот режим уже включен")

    async def responce_state_is_busy(self, current_state):
        """Это шаблон ответа, что запрашиваемый режим включить нельзя
        :param current_state: str
        """
        message = f"Активирован режим {current_state}, включить не можем"
        raise web.HTTPBadRequest(text=message)

    async def unit_activation(self, params):
        """Этот метод активирует узел
        :param params: dict вида {"unit_type": str,
                                  "unit_id": uuid}
        """
        unit_type = params["unit_type"]
        unit_id = params["unit_id"]
        try:
            if unit_type != "ovens":
                print("Меняем данные оборудования")
                getattr(self.equipment, unit_type)[unit_id] = True
            else:
                print("Меняем данные печи")
                self.equipment.ovens.oven_units[unit_id].status = "free"
            return SUCCEED_FUTURA_RESULT
        except KeyError:
            return "Данные не найдены"

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

    async def create_on_start_tasks(self, app, scheduler):
        """Этот метод запускает сервер, планировщик и фоновые задачи, запускаемые на старте"""
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=SERVER_HOST, port=SERVER_PORT)
        await site.start()
        scheduler.start()

        on_start_tasks = asyncio.create_task(self.add_equipment_data())
        controllers_bus = asyncio.create_task(event_generator(self.events_monitoring, self.equipment))
        event_listener = asyncio.create_task(self.create_hardware_broke_listener())
        is_able_to_cook_monitor = asyncio.create_task(self.is_able_to_cook_monitoring())
        # discord_sender = asyncio.create_task(self.discord_bot_client.start_working())
        message_monitoring = asyncio.create_task(self.message_sending_worker())

        await asyncio.gather(controllers_bus, event_listener, is_able_to_cook_monitor,
                            message_monitoring, on_start_tasks)

        # await asyncio.gather(controllers_bus, event_listener, is_able_to_cook_monitor,
        #                      discord_sender, message_monitoring, on_start_tasks)

    def start_server(self):
        """Это основай метод запуска работы приложения"""
        app = self.create_server()
        scheduler = self.create_scheduler()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.create_on_start_tasks(app, scheduler))
        loop.run_forever()
