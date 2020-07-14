import asyncio
from aiohttp import web

from ..data.server.server_const import ServerConfig
from .handlers import Handlers
from ..task_manager.pbm import pizza_bot_main
# from .scheduler import create_scheduler
from .scheduler import PbmScheduler
from kbs.cntrls_api.ControllerBus import event_generator


class Server():

    def create_server(self):
        """Этот метод создает объект aiohttp сервера, а также привязывает к серверу routes api
        для связи с внешними компонентами (админ панель и экран приема заказов)
        :return: экземпляр класса aiohttp.web
        """

        app = web.Application()
        self.setup_routes(app)
        return app

    def setup_routes(self, app):
        """ Этот метод связывает доступные эндпоинты и обработчики запросов.
        :param app: экземпляр класса aiohttp.web
        """
        app.add_routes([
            web.get("/api/current_state", Handlers.kiosk_current_state_handler),
            web.post("/api/new_order", Handlers.new_order_handler),
            web.post("/api/commands/cooking_mode", Handlers.turn_on_cooking_mode_handler),
            web.get("/api/commands/status", Handlers.status_command_handler),
            # web.post("/api/commands/stopping_cooking_mode", Handlers.turn_off_cooking_mode_handler),
            web.post("/api/commands/full_system_testing", Handlers.start_full_testing_handler),
            web.post("/api/commands/unit_testing", Handlers.start_unit_testing_handler),
            web.post("/api/commands/unit_activation", Handlers.unit_activation_handler),
        ])

    async def create_on_start_tasks(self, app, scheduler):
        """Этот метод запускает сервер, планировщик и фоновые задачи, запускаемые на старте"""
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=ServerConfig.SERVER_HOST,
                           port=ServerConfig.SERVER_PORT)
        await site.start()
        scheduler.scheduler.start()

        on_start_tasks = asyncio.create_task(pizza_bot_main.add_equipment_data())
        controllers_bus = asyncio.create_task(event_generator(pizza_bot_main.events_monitoring,
                                                              pizza_bot_main.equipment))
        event_listener = asyncio.create_task(pizza_bot_main.create_hardware_broke_listener())
        is_able_to_cook_monitor = asyncio.create_task(pizza_bot_main.is_able_to_cook_monitoring())
        # discord_sender = asyncio.create_task(self.discord_bot_client.start_working())
        message_monitoring = asyncio.create_task(pizza_bot_main.message_sending_worker())

        await asyncio.gather(controllers_bus, event_listener, is_able_to_cook_monitor, message_monitoring,
                             on_start_tasks)

    def start_server(self):
        """Это основай метод запуска работы приложения"""
        app = self.create_server()
        scheduler = PbmScheduler()
        # scheduler = create_scheduler()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.create_on_start_tasks(app, scheduler))
        loop.run_forever()
