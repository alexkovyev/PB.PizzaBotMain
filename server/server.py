""" Этот модуль описывает http сервер и фоновые задачи, запускаемые на старте"""
import asyncio
from aiohttp import web
import time
import uuid

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config.config import (SERVER_HOST, SERVER_PORT,
                           STANDBYMODE, BEFORECOOKING, COOKINGMODE, TESTINGMODE)
from controllers.ControllerBus import ControllersEvents, event_generator
from server.equipment import Equipment
from kiosk_state.CookingMode import CookingMode
from kiosk_state import StandByMode, TestingMode
from logs.logs import PBlogs


class PizzaBotMain(object):
    """ Это основной класс приложения, запускаемый при старте системы """

    def __init__(self):
        self.current_state = STANDBYMODE
        self.current_instance = StandByMode.StandBy()
        self.equipment = None
        self.events_monitoring = ControllersEvents()
        self.command_status = {}

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
        scheduler.add_job(self.turn_on_cooking_mode, 'cron', day_of_week='*', hour='23', minute=50, second=0)
        scheduler.add_job(self.turn_off_cooking_mode, 'cron', day_of_week='*', hour='21', minute=0, second=0)
        scheduler.add_job(self.turn_off_cooking_mode, 'cron', day_of_week='*', hour='22', minute=0, second=0)
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
            # web.post("/api/commands/unit_testing"),,
            # web.post(r"/api/commands/activation/{unit_id}"),
            # web.post(r"/api/commands/de-activation/{unit_id}"),
        ])

    # API handlers
    async def new_order_handler(self, request):
        """Этот метод обрабатывает запросы приема новых заказов в зависимости от текущего режима киоска,
        запускает создание нового заказа при необходимости.
        """
        print("Получили запрос от SS на новый заказ", time.time())
        if not request.body_exists:
            raise web.HTTPNoContent
        request_body = await request.json()
        new_order_id = request_body["check_code"]
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
        print("Получили запрос текущего статуса киоска")
        current_state = self.current_state
        return web.Response(text=current_state)

    async def turn_cooking_mode_handler(self, request):
        """Этот метод обрабатывает запроса на включение режима готовки """
        print("Получили запрос на включение режима готовки")
        if self.current_state == COOKINGMODE or self.current_state == BEFORECOOKING:
            await self.state_is_already_on_responce()

        elif self.current_state == STANDBYMODE:
            response = await self.turn_any_mode(self.cooking_mode_start)
            return web.Response(text=response)

        elif self.current_state == TESTINGMODE:
            print("Идет тестирование, включить не можем")
            raise web.HTTPBadRequest(text="Идет тестирование, включить не можем")

    async def turn_off_cooking_mode_handler(self, request):
        print("Получили запрос на включение режима готовки")
        pass

    async def start_full_testing_handler(self, request):
        print("Получили запрос на включение режима готовки")
        if self.current_state == COOKINGMODE:
            pass

        elif self.current_state == STANDBYMODE:
            response = await self.turn_any_mode(self.testing_start)
            return web.Response(text=response)

        elif self.current_state == TESTINGMODE:
            await self.state_is_already_on_responce()

    # Schedule handlers
    async def turn_on_testing_mode(self, mode):
        pass

    async def turn_on_cooking_mode(self):
        """Этот метод запускает режим готовки"""
        IMPOSSIBLE_TO_TURN_ON_STATES = [TESTINGMODE, COOKINGMODE, BEFORECOOKING]
        if self.current_state == STANDBYMODE:
            await self.cooking_mode_start()
        elif self.current_state in IMPOSSIBLE_TO_TURN_ON_STATES:
            print("киоск занят, не могу включить")
        print("Режим готовки активирован", self.current_state)

    async def turn_off_cooking_mode(self):
        pass

    # utils for handlers
    async def cooking_mode_start(self, future=None):
        print("ЗАПУСКАЕМ режим ГОТОВКИ")
        self.current_state = BEFORECOOKING
        self.current_instance = CookingMode.BeforeCooking()
        if self.equipment is None:
            print("ОШИБКА ОБОРУДОВАНИЯ")
            self.equipment = await self.add_equipment_data()
        (is_ok, self.equipment), recipe = await CookingMode.BeforeCooking.start_pbm(self.equipment)
        await asyncio.sleep(20)
        self.current_instance = CookingMode.CookingMode(recipe, self.equipment)
        self.current_state = COOKINGMODE
        if future is not None and not future.cancelled():
            future.set_result("200 OK")
        await self.current_instance.cooking()

    async def testing_start(self, future=None):
        """ Это супер метод тестов"""
        print("Запускаем тестирование, долгое")
        self.current_state = TESTINGMODE
        self.current_instance = TestingMode.TestingMode()
        await asyncio.sleep(60)
        self.current_state = STANDBYMODE
        self.current_instance = StandByMode.StandBy()
        if future is not None and not future.cancelled():
            future.set_result("200 OK")

    async def is_open_for_new_orders(self):
        """Метод определяет можно ли принимать заказы"""
        return True if self.current_state == COOKINGMODE else False

    async def get_futura_result(self, futura):
        if futura.done():
            try:
                my_result = futura.result()
                print(my_result)
                print(type(my_result))
            except asyncio.CancelledError:
                my_result = "command was cancelled"
        else:
            my_result = "proceeding"
        return my_result

    async def status_command(self, request):
        print("Запрос на статус команды")
        if not request.body_exists:
            raise web.HTTPNoContent
        request_body = await request.json()
        command_uuid = request_body["command_uuid"]
        try:
            result = await self.get_futura_result(self.command_status[command_uuid])
            if result == "200 OK":
                self.command_status.pop(command_uuid)
            return web.Response(text=result)
        except KeyError:
            raise web.HTTPBadRequest(text="uuid не найден")

    async def create_result_future(self):
        operation_result = asyncio.get_running_loop().create_future()
        operation_result_uuid = str(uuid.uuid4())
        self.command_status[operation_result_uuid] = operation_result
        return operation_result_uuid, operation_result

    async def turn_any_mode(self, task_name):
        print("Ок, включаем")
        operation_result_uuid, operation_result = await self.create_result_future()
        asyncio.create_task(task_name(operation_result))
        response = f"uuid:{operation_result_uuid}"
        return response

    async def state_is_already_on_responce(self):
        print("Этот режим уже включен")
        raise web.HTTPNotAcceptable(text="Этот режим уже включен")

    #on_start_tasks
    async def create_hardware_broke_listener(self):
        """Этот метод запускает бесконечный таск, который отслеживает наступление событий
         поломки оборудования"""
        event_name = "hardware_status_changed"
        event = self.events_monitoring.get_dispatcher_event(event_name)
        while True:
            event_occurrence = await event
            _, event_params = event_occurrence
            print("Сработало событие, обрабатываем")
            await self.current_instance.broken_equipment_handler(event_params)

    async def get_equipment_data(self):
        await asyncio.sleep(10)
        oven_ids = [str(uuid.uuid4()) for i in range(1, 22)]
        equipment_data = {
            "ovens": {i: {"oven_id": i, "status": "free"} for i in oven_ids},
            "cut_station": {"id": "f50ec0b7-f960-400d-91f0-c42a6d44e3d0",
                            "status": "ok"},
            "package_station": {"id": "afeb1c10-83ef-4194-9821-491fcf0aa52b",
                                "status": "ok"},
            "sauce_dispensers": {"16ffcee8-2130-4a2f-b71d-469ee65d42d0": "ok",
                                 "ab5065e3-93aa-4313-869e-50a959458439": "ok",
                                 "28cc0239-2e35-4ccd-9fcd-be2155e4fcbe": "ok",
                                 "1b1af602-b70f-42a3-8b5d-3112dcf82c26": "ok",
                                 },
            "dough_dispensers": {"ebf29d04-023c-4141-acbe-055a19a79afe": "ok",
                                 "2e84d0fd-a71f-4988-8eee-d0373c0bc609": "ok",
                                 "68ec7c16-f57b-43c0-b708-dfaea5c2e1dd": "ok",
                                 "75355f3c-bf05-405d-98af-f04bcba7d7e4": "ok",
                                 },
            "pick_up_points": {"1431f373-d036-4e0f-b059-70acd6bd18b9": "ok",
                               "b7f96101-564f-4203-8109-014c94790978": "ok",
                               "73b194e1-5926-45be-99ec-25e1021b96f7": "ok",
                               }
        }
        return equipment_data

    async def add_equipment_data(self):
        """Этот метод запускает сбор данных об оборудовании из БД и создает экземпляр класса Equipment"""
        equipment_data = await self.get_equipment_data()
        self.equipment = Equipment(equipment_data)

    async def create_on_start_tasks(self, app, scheduler):
        """Этот метод запускает сервер, планировщик и фоновые задачи, запускаемые на старте"""
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=SERVER_HOST, port=SERVER_PORT)
        await site.start()
        scheduler.start()

        on_start_tasks = asyncio.create_task(self.add_equipment_data())
        controllers_bus = asyncio.create_task(event_generator(self.events_monitoring))
        event_listener = asyncio.create_task(self.create_hardware_broke_listener())

        await asyncio.gather(controllers_bus, event_listener, on_start_tasks)

    def start_server(self):
        """Это основай метод запуска работы приложения"""
        app = self.create_server()
        scheduler = self.create_scheduler()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.create_on_start_tasks(app, scheduler))
        loop.run_forever()
