import asyncio
from aiohttp import web

from ..data.server.server_const import ServerConfig
from .handlers import Handlers


class Server():

    @classmethod
    def create_server(clx):
        """Этот метод создает объект aiohttp сервера, а также
        привязывает к серверу routes api для связи с внешними
        компонентами (админ панель и экран приема заказов)
        :return: экземпляр класса aiohttp.web
        """

        app = web.Application()
        clx.setup_routes(app)

        return app

    @classmethod
    def setup_routes(clx, app):
        """ Этот метод связывает доступные эндпоинты и обработчики запросов.
        :param app: экземпляр класса aiohttp.web
        """
        app.add_routes([
            web.get("/api/current_state", Handlers.kiosk_current_state_handler),
            web.post("/api/new_order", Handlers.new_order_handler),
            # web.post("/api/commands/maintenance"),
            web.post("/api/receive_order", Handlers.can_receive_order),
            web.post("/api/commands/cooking_mode", Handlers.turn_on_cooking_mode_handler),
            web.get("/api/commands/status", Handlers.status_command_handler),
            # web.post("/api/commands/stopping_cooking_mode",
            #          Handlers.turn_off_cooking_mode_handler),
            web.post("/api/commands/full_system_testing", Handlers.start_full_testing_handler),
            web.post("/api/commands/unit_testing", Handlers.start_unit_testing_handler),
            web.post("/api/commands/unit_activation", Handlers.unit_activation_handler),
        ])

    @staticmethod
    async def create_on_start_tasks(app, scheduler):
        """Этот метод запускает сервер, планировщик и фоновые задачи, запускаемые на старте"""
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=ServerConfig.SERVER_HOST,
                           port=ServerConfig.SERVER_PORT)
        await site.start()
        scheduler.scheduler.start()
        await app["state"].add_equipment_data()

        # controllers_bus = asyncio.create_task(event_generator(pizza_bot_main.events_monitoring,
        #                                                       pizza_bot_main.equipment))
        is_able_to_cook_monitor = asyncio.create_task(app["state"].is_able_to_cook_monitoring())
        # event_binder = asyncio.create_task(pizza_bot_main.event_handlers_binder())
        # discord_sender = asyncio.create_task(self.discord_bot_client.start_working())
        message_monitoring = asyncio.create_task(app["state"].message_sending_worker())

        await asyncio.gather(message_monitoring, is_able_to_cook_monitor)

        # await asyncio.gather(controllers_bus, event_binder,
        #                      is_able_to_cook_monitor,
        #                      message_monitoring)
