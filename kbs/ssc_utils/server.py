import asyncio
from aiohttp import web

from .handlers import Handlers
from .scheduler import create_scheduler


class Server():

    def __init__(self):
        self.command_status = {}

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

    def start_server(self):
        """Это основай метод запуска работы приложения"""
        app = self.create_server()
        scheduler = create_scheduler()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.create_on_start_tasks(app, scheduler))
        loop.run_forever()
