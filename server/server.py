import asyncio
from aiohttp import web
import time
import uuid

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config.config import SERVER_HOST, SERVER_PORT
from controllers.ControllerBus import ControllersEvents, event_generator
from notifications.discord_sender import DiscordBotSender
from server.equipment import Equipment
from kiosk_modes.CookingMode import CookingMode
from kiosk_modes import (StandByMode)
from logs.logs import PBlogs


class PizzaBotMain(object):

    def __init__(self):
        self.kiosk_status = "stand_by"
        self.is_kiosk_busy = False
        self.current_instance = StandByMode.StandBy()
        self.equipment = None
        self.cntrls_events = ControllersEvents()
        self.config = None

    def create_server(self):
        app = web.Application()
        self.setup_routes(app)
        return app

    def setup_routes(self, app):
        app.add_routes([
            web.post("/api/new_order", self.new_order_handler),
            web.get("/", self.hello),
            # все доступные команды
            # web.get("/api/commands", None),
            # web.post("/api/commands/cooking_mode", None)
        ])

    async def hello(self, request):
        return web.Response(text="Тут все работает")

    async def new_order_handler(self, request):
        print("Получили запрос от SS на новый заказ", time.time())
        if request.body_exists:
            request_body = await request.json()
            new_order_id = request_body["check_code"]
            can_receive_new_order = await self.is_open_for_new_orders()
            if can_receive_new_order:
                try:
                    is_it_new_order = await self.current_instance.checking_order_for_double(new_order_id)
                    print("Это новый заказ")
                    if is_it_new_order:
                        print("В этом ифе")
                        print(self.current_instance.create_new_order)
                        print(self.equipment.oven_available)
                        await asyncio.create_task(self.current_instance.create_new_order(new_order_id,
                                                                                   self.equipment.oven_available))
                        message = "Заказ успешно принят"
                        raise web.HTTPCreated(text=message)
                    else:
                        message = "Этот заказ уже находится в обработке"
                        raise web.HTTPOk(text=message)
                except AttributeError as e:
                    print("Не создан инстанс cooking mode или метод не найден")
                    print(e)
                    raise web.HTTPServerError(text="Ошибка века в сервере")
            else:
                message = "Заказы не принимаем, приходите завтра"
                raise web.HTTPNotAcceptable(text=message)
        else:
            raise web.HTTPNoContent

    def create_scheduler(self):
        scheduler = AsyncIOScheduler()
        scheduler.add_job(self.test_scheduler, 'interval', seconds=5)
        # переделать на включение в определенный момент
        scheduler.add_job(self.turn_on_cooking_mode, 'cron', day_of_week='*', hour='0', minute=23, second=30)
        return scheduler

    def get_config_data(self):
        pass

    async def get_equipment_data(self):
        print("Подключаемся к БД за информацией", time.time())
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
        print("Получили данные из БД", time.time())
        return equipment_data

    async def add_equipment_data(self):
        print("Начинаем собирать данные об оборудовании", time.time())
        equipment_data = await self.get_equipment_data()
        self.equipment = Equipment(equipment_data)
        print("Закончили собирать данные об оборудовании", time.time())

    async def is_open_for_new_orders(self):
        return True if self.kiosk_status == "cooking" else False

    async def turn_on_cooking_mode(self):
        """Включить можно только после завершения тестов"""
        if self.kiosk_status == "stand_by":
            print("ЗАПУСКАЕМ режим ГОТОВКИ")
            self.current_instance = CookingMode.BeforeCooking()
            if self.equipment is None:
                print("ОШИБКА ОБОРУДОВАНИЯ")
                self.equipment = await self.add_equipment_data()
            (is_ok, self.equipment), recipe = await CookingMode.BeforeCooking.start_pbm(self.equipment)
            self.current_instance = CookingMode.CookingMode(recipe)
            self.kiosk_status = "cooking"
            await self.current_instance.cooking()
        elif self.kiosk_status == "testing_mode":
            pass
        elif self.kiosk_status == "cooking":
            pass
        print("Режим готовки активирован", self.kiosk_status)

    async def test_working(self):
        while True:
            print("запускается фоновая задача", time.time())
            print("Текущий режим", self.current_instance)
            await asyncio.sleep(5)
            print("фоновая задача отработала", time.time())

    async def test_scheduler(self):
        print("Привет из расписания", time.time())

    async def create_hardware_broke_listener(self):
        event_name = "hardware_status_changed"
        event = self.cntrls_events.get_dispatcher_event(event_name)
        while True:
            event_data = await event
            _, new_data = event_data
            await self.hardware_broke_handler(new_data)

    async def hardware_broke_handler(self, event_data):
        print("Обрабатываем уведомление об поломке оборудования", time.time())
        oven_id = int(event_data["unit_name"])
        oven_status = event_data["status"]
        print("Обработали", oven_id, oven_status)

    async def create_tasks(self, app, scheduler):
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=SERVER_HOST, port=SERVER_PORT)
        await site.start()
        scheduler.start()

        # Переделать потом на генерацию из списка
        on_start_tasks = asyncio.create_task(self.add_equipment_data())
        controllers_bus = asyncio.create_task(event_generator(self.cntrls_events))
        event_listener = asyncio.create_task(self.create_hardware_broke_listener())
        discord_sender = asyncio.create_task(DiscordBotSender.send_message())
        test_task = asyncio.create_task(self.test_working())
        logging_task = asyncio.create_task(PBlogs.logging_task())

        await asyncio.gather(controllers_bus, test_task, event_listener, discord_sender, logging_task,
                             on_start_tasks)

    def start_server(self):
        app = self.create_server()
        scheduler = self.create_scheduler()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.create_tasks(app, scheduler))
        loop.run_forever()
